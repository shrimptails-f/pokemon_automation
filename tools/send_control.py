"""Send one controller command through the current Arduino protocol."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from automation.adapters.serial_controller import BUTTONS, HATS, SerialController


def main():
    parser = argparse.ArgumentParser(description="Arduino に操作を1回送信する")
    parser.add_argument("port", help="SH-U09C のポート（例: COM8）")
    parser.add_argument("command", type=str.upper, help="操作: " + ", ".join((*BUTTONS, *HATS, "STICK_UP")))
    parser.add_argument("duration_ms", nargs="?", type=int, help="STICK_UP の時間（ミリ秒）")
    args = parser.parse_args()

    if args.command == "STICK_UP":
        if args.duration_ms is None or not 1 <= args.duration_ms <= 3000:
            parser.error("STICK_UP には 1〜3000 ミリ秒を指定してください")
        command = f"STICK_UP {args.duration_ms}"
    elif args.command in BUTTONS or args.command in HATS:
        if args.duration_ms is not None:
            parser.error("押下時間は STICK_UP のみ指定できます")
        command = args.command
    else:
        parser.error("不明な操作です。指定可能: " + ", ".join((*BUTTONS, *HATS, "STICK_UP")))

    try:
        with SerialController(args.port) as controller:
            controller.send(command)
        print(f"操作を送信しました: {command}")
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        sys.exit(f"操作に失敗しました: {exc}")


if __name__ == "__main__":
    main()
