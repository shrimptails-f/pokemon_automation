"""Send one button press per line over the SH-U09C serial adapter."""
import argparse
import sys

try:
    import serial
except ImportError:
    sys.exit("pyserial が必要です: py -m pip install pyserial")

BUTTONS = {"A", "B", "X", "Y", "L", "R", "ZL", "ZR", "PLUS", "MINUS",
           "HOME", "CAPTURE", "UP", "DOWN", "LEFT", "RIGHT"}


def main():
    parser = argparse.ArgumentParser(description="Switch controller test")
    parser.add_argument("port", help="SH-U09C のポート (例: COM5)")
    args = parser.parse_args()
    try:
        with serial.Serial(args.port, 115200, timeout=2, write_timeout=2) as port:
            port.reset_input_buffer()
            port.write(b"PING\n")
            if port.readline().strip() != b"PONG":
                sys.exit("Arduino から応答がありません。配線とポートを確認してください。")
            print("接続しました。ボタン名を入力してください。終了: quit")
            print("利用可能: " + ", ".join(sorted(BUTTONS)))
            while True:
                try:
                    button = input("> ").strip().upper()
                except EOFError:
                    break
                if button in {"QUIT", "EXIT"}:
                    break
                if button not in BUTTONS:
                    print("不明なボタンです。")
                    continue
                port.write((button + "\n").encode("ascii"))
                response = port.readline().strip()
                if response != b"OK":
                    sys.exit(f"応答エラー: {response!r}。操作を停止します。")
                print("送信しました")
    except (serial.SerialException, OSError) as exc:
        sys.exit(f"シリアル通信エラー: {exc}")
    except KeyboardInterrupt:
        print()


if __name__ == "__main__":
    main()
