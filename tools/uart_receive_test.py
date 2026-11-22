"""Compare SH-U09C transmission with Arduino USB output, without Switch input."""
import argparse
import secrets
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="SH-U09C から Arduino への UART 受信を診断")
    parser.add_argument("adapter_port", help="SH-U09C の COM ポート")
    parser.add_argument("arduino_port", help="Arduino USB シリアルの COM ポート")
    parser.add_argument("--count", type=int, default=1000, help="送信回数（既定: 1000）")
    args = parser.parse_args()
    if args.count < 1:
        parser.error("回数は1以上を指定してください")
    if args.adapter_port.upper() == args.arduino_port.upper():
        parser.error("SH-U09C と Arduino は異なるポートを指定してください")

    try:
        import serial
        with serial.Serial(args.arduino_port, 115200, timeout=0.1) as arduino, \
             serial.Serial(args.adapter_port, 115200, timeout=0.1, write_timeout=2) as adapter:
            time.sleep(2)
            arduino.reset_input_buffer()
            arduino.write(b'?')
            ready = arduino.readline()
            if ready.strip() != b'UART-DIAG-READY':
                sys.exit(f"ERROR: Arduino USB diagnostic did not respond: {ready!r}")
            print("ARDUINO USB: OK", flush=True)
            ok = 0
            failures = 0
            print(f"START: {args.count} packets", flush=True)
            for i in range(args.count):
                sent = f"{i:08X}{secrets.token_hex(4).upper()}\n".encode('ascii')
                adapter.write(sent)
                received = arduino.readline()
                if received == sent:
                    ok += 1
                else:
                    failures += 1
                    if failures <= 10:
                        print(f"FAIL {i + 1}: sent={sent!r} received={received!r}", flush=True)
                if (i + 1) % 100 == 0:
                    print(f"PROGRESS: {i + 1}/{args.count}, OK={ok}, FAIL={failures}", flush=True)
            print(f"RESULT: total={args.count}, OK={ok}, FAIL={failures}", flush=True)
    except (ImportError, OSError) as exc:
        sys.exit(f"ERROR: {exc}")


if __name__ == "__main__":
    main()
