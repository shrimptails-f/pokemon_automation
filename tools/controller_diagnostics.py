"""Read fixed-size Arduino diagnostics without starting a controller session."""
import argparse
from pathlib import Path
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.adapters.controller_protocol import decode_frame, encode_frame


def read_diagnostics(port, *, timeout=0.5, attempts=3):
    session = secrets.randbits(32) or 1
    request = encode_frame(f"2,{session},0,DIAG")
    for _ in range(attempts):
        port.write(request)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            port.timeout = min(0.15, max(0, deadline - time.monotonic()))
            raw = port.readline()
            try:
                fields = decode_frame(raw).split(",")
            except ValueError:
                continue
            if len(fields) != 5 or fields[:4] != ["2", str(session), "0", "DIAG"]:
                continue
            parts = fields[4].split(":")
            if len(parts) != 10 or any(not x.isascii() or not x.isdigit() for x in parts[:9]):
                raise ValueError("診断応答の形式が不正です")
            if parts[9] not in {"NONE", "RUNNING", "DONE", "USB", "EXPIRED"}:
                raise ValueError("診断結果が不正です")
            return tuple(map(int, parts[:9])) + (parts[9],)
    raise TimeoutError("診断応答がありません。配線・電源・ファームウェアを確認してください")


def main():
    parser = argparse.ArgumentParser(description="Arduino の通信診断情報を読み取る")
    parser.add_argument("port", help="SH-U09C のポート（例: COM8）")
    args = parser.parse_args()
    try:
        import serial
        with serial.Serial(args.port, 115200, timeout=0.15, write_timeout=0.5) as port:
            port.write(b"\n")
            port.reset_input_buffer()
            received, rejected, replies, crc, malformed, timeout, overflow, session, sequence, result = read_diagnostics(port)
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        sys.exit(f"診断情報を取得できませんでした: {exc}")
    print(f"正常な要求: {received} / 破棄した行: {rejected} / 応答の送信試行: {replies}")
    print(f"破棄理由: CRC 不一致={crc} / 形式不正={malformed} / 途中行期限切れ={timeout} / 長さ超過={overflow}")
    print(f"最後に受け付けた時間指定操作: セッション={session} 番号={sequence} 状態={result}")
    print("値は Arduino の起動後からの累積です。正常な要求は今回の診断要求を含み、応答の送信試行は今回の応答を含みません。")


if __name__ == "__main__":
    main()
