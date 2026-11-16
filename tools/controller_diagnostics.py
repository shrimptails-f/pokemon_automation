"""Read fixed-size Arduino diagnostics without starting a controller session."""
import argparse
from pathlib import Path
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.adapters.controller_protocol import decode_frame, encode_frame


def exchange(port, command, *, timeout=0.5, attempts=3, session=None, sequence=0):
    """Match a response; keep partial reads until LF and retry the same request."""
    session = session or secrets.randbits(32) or 1
    operation = command.split(",", 1)[0]
    request = encode_frame(f"2,{session},{sequence},{command}")
    pending = bytearray()
    discarding = False
    for attempt in range(1, attempts + 1):
        if hasattr(port, "event"):
            port.event("request", operation=operation, sequence=sequence, attempt=attempt)
        port.write(request)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            port.timeout = min(0.15, max(0, deadline - time.monotonic()))
            raw = port.readline()
            for byte in raw:
                if byte == 10:
                    frame = bytes(pending) + b"\n"
                    pending.clear()
                    if discarding:
                        discarding = False
                        continue
                    try:
                        fields = decode_frame(frame).split(",")
                    except ValueError:
                        continue
                    if len(fields) == 5 and fields[:4] == ["2", str(session), str(sequence), operation]:
                        return fields[4]
                elif not discarding:
                    pending.append(byte)
                    if len(pending) >= 160:
                        pending.clear()
                        discarding = True
        if hasattr(port, "event"):
            port.event("timeout", operation=operation, sequence=sequence, attempt=attempt)
    raise TimeoutError(f"{operation} の応答がありません（送信 {attempts} 回）")


def read_diagnostics(port, *, timeout=0.5, attempts=3):
    result = exchange(port, "DIAG", timeout=timeout, attempts=attempts)
    parts = result.split(":")
    if len(parts) != 11 or any(not x.isascii() or not x.isdigit() for x in parts[:10]):
        raise ValueError("診断応答の形式が不正です")
    if parts[10] not in {"NONE", "RUNNING", "DONE", "USB", "EXPIRED"}:
        raise ValueError("診断結果が不正です")
    return tuple(map(int, parts[:10])) + (parts[10],)


def main():
    parser = argparse.ArgumentParser(description="Arduino の通信診断情報を読み取る")
    parser.add_argument("port", help="SH-U09C のポート（例: COM8）")
    args = parser.parse_args()
    try:
        import serial
        with serial.Serial(args.port, 115200, timeout=0.15, write_timeout=0.5) as port:
            port.write(b"\n")
            port.reset_input_buffer()
            received, rejected, replies, crc, malformed, timeout, overflow, noise, session, sequence, result = read_diagnostics(port)
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        sys.exit(f"診断情報を取得できませんでした: {exc}")
    print(f"正常な要求: {received} / 破棄した行: {rejected} / 応答の送信試行: {replies}")
    print(f"破棄理由: CRC 不一致={crc} / 形式不正={malformed} / 途中行期限切れ={timeout} / 長さ超過={overflow}")
    print(f"先頭ノイズとして捨てたバイト: {noise}")
    print(f"最後に受け付けた時間指定操作: セッション={session} 番号={sequence} 状態={result}")
    print("値は Arduino の起動後からの累積です。正常な要求は今回の診断要求を含み、応答の送信試行は今回の応答を含みません。")


if __name__ == "__main__":
    main()
