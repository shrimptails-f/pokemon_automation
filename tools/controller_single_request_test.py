"""Send non-retried STATUS requests and retain evidence even if DIAG fails."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools.controller_capture import LoggedPort, report_capture
from tools.controller_diagnostics import exchange, read_diagnostics


def run(port, rounds, wait):
    session = secrets.randbits(32) or 1
    last_crc = 0
    try:
        for seq in range(1, rounds + 1):
            before = read_diagnostics(port, timeout=wait, attempts=1)
            if before[3] > last_crc:
                report_capture(port, timeout=wait)
                before = read_diagnostics(port, timeout=wait, attempts=1)
            last_crc = before[3]
            started = time.monotonic()
            try:
                status = exchange(port, 'STATUS', session=session, sequence=seq, timeout=wait, attempts=1)
                result = f'{status} ({time.monotonic() - started:.3f}秒)'
            except TimeoutError:
                result = f'{wait:g}秒以内に確認できず'
            # Log STATUS before DIAG, so DIAG failure cannot hide its result.
            port.event('status_result', sequence=seq, result=result)
            print(f'{seq}: STATUS応答={result}', flush=True)
            after = read_diagnostics(port, timeout=wait, attempts=1)
            delta = dict(received=after[0]-before[0]-1, replies=after[2]-before[2]-1,
                         rejected=after[1]-before[1], crc=after[3]-before[3])
            port.event('counters', sequence=seq, before=before, after=after, delta=delta)
            print(f"  正常要求の増分={delta['received']} / 応答送信試行の増分={delta['replies']} / "
                  f"破棄行の増分={delta['rejected']} / CRC不一致の増分={delta['crc']}", flush=True)
            if delta['rejected'] > 0 or result.endswith('確認できず'):
                report_capture(port, timeout=wait)
            last_crc = after[3]
    except (OSError, ValueError, RuntimeError) as exc:
        port.event('test_error', error=str(exc))
        print(f'診断を中断しました: {exc}', flush=True)
        # Even a failed DIAG may itself have become the captured CRC failure.
        report_capture(port, timeout=wait)
        return False
    return True


def main():
    parser = argparse.ArgumentParser(description='再送なし STATUS の比較と受信破損の記録（115200 bps）')
    parser.add_argument('port')
    parser.add_argument('--rounds', type=int, default=100)
    parser.add_argument('--wait', type=float, default=1.0)
    parser.add_argument('--log', type=Path, default=Path('controller-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.jsonl'))
    args = parser.parse_args()
    if args.rounds < 1 or not 0 < args.wait < float('inf'):
        parser.error('回数と待ち時間は正の有限値にしてください')
    try:
        import serial
        # Exclusive creation prevents accidental loss of an earlier trace.
        with args.log.open('x', encoding='utf-8') as log:
            print(f'ログ: {args.log.resolve()}', flush=True)
            with serial.Serial(args.port, 115200, timeout=0.15, write_timeout=0.5) as serial_port:
                port = LoggedPort(serial_port, log)
                port.event('start', port=args.port, baudrate=115200, rounds=args.rounds, wait=args.wait)
                port.write(b'\n')
                time.sleep(0.5)
                success = run(port, args.rounds, args.wait)
                port.event('finish', success=success)
                return 0 if success else 1
    except (OSError, ImportError) as exc:
        print(f'診断を開始・継続できませんでした: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
