"""Repeat encounters with a human review before every game restart."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import tempfile

try:
    import serial
except ImportError:
    sys.exit("pyserial が必要です: python -m pip install pyserial")


def send(port, button):
    port.write((button + "\n").encode("ascii"))
    response = port.readline().strip()
    if response != b"OK":
        raise RuntimeError(f"{button} の応答エラー: {response!r}")
    print(f"{button} を送信", flush=True)


def main():
    parser = argparse.ArgumentParser(description="画像を確認しながら遭遇を繰り返す")
    parser.add_argument("port", help="SH-U09C の COM ポート")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--move-ms", type=int, required=True)
    parser.add_argument("--a-after", type=float, required=True)
    parser.add_argument("--auto-reset", action="store_true", help="通常色の可能性なら自動で再起動")
    args = parser.parse_args()
    if not 1 <= args.move_ms <= 3000 or not 0 <= args.a_after <= 120 or args.device < 0:
        parser.error("move-ms は 1〜3000、a-after は 0〜120、device は 0 以上にしてください")
    script = Path(__file__).with_name("encounter_capture.py")
    attempt = 0
    try:
        while True:
            attempt += 1
            print(f"\n{attempt} 回目: 遭遇と撮影", flush=True)
            with tempfile.TemporaryDirectory(prefix="bdsp-result-") as temp_dir:
                result_path = Path(temp_dir) / "result.txt"
                result = subprocess.run([sys.executable, str(script), args.port, "--device", str(args.device),
                                         "--move-ms", str(args.move_ms), "--a-after", str(args.a_after),
                                         "--delay", "4.5", "--duration", "1.5", "--interval", "0.25",
                                         "--result-file", str(result_path)])
                if result.returncode != 0 or not result_path.is_file():
                    sys.exit("撮影または判定に失敗したため停止します。")
                classification = result_path.read_text(encoding="ascii").strip()
            if args.auto_reset:
                if classification != "normal":
                    print("通常色と判定できなかったため停止します。画像を確認してください。")
                    return
                print("通常色の可能性: 自動で再起動します。", flush=True)
            else:
                answer = input("保存された画像を確認し、通常色なら reset、停止するなら Enter: ").strip().lower()
                if answer != "reset":
                    print("停止しました。")
                    return
            with serial.Serial(args.port, 115200, timeout=5, write_timeout=2) as port:
                port.write(b"\n")
                time.sleep(0.5)
                port.reset_input_buffer()
                port.write(b"PING\n")
                if port.readline().strip() != b"PONG":
                    raise RuntimeError("Arduino の接続確認に失敗しました。")
                for button in ("HOME", "X", "A", "A", "A"):
                    send(port, button)
                    time.sleep(2)
                # Count 13 seconds from the last A release, including the 2 seconds above.
                time.sleep(11)
                send(port, "A")
                time.sleep(2)
                send(port, "A")
                time.sleep(2)
                send(port, "A")
                print("7 秒待ってから次の撮影を行います。", flush=True)
                time.sleep(7)
    except (serial.SerialException, OSError, RuntimeError) as exc:
        sys.exit(f"操作を停止しました: {exc}")
    except (KeyboardInterrupt, EOFError):
        print("\n停止しました。")


if __name__ == "__main__":
    main()
