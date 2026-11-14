"""Capture and classify one encounter."""
import argparse
from pathlib import Path
import shutil
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from automation.adapters.opencv_capture import OpenCVCapture
from automation.adapters.serial_controller import SerialController
from title.BDSP.pokemon.arceus.encounter import encounter


def main():
    parser = argparse.ArgumentParser(description="前進して遭遇場面を撮影する")
    parser.add_argument("port")
    parser.add_argument("--move-ms", required=True, type=int)
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--a-after", required=True, type=float)
    parser.add_argument("--delay", type=float, default=3.0)
    parser.add_argument("--duration", type=float, default=5.0)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument("--output", type=Path, default=Path.home() / "Pictures" / "BDSP-captures")
    parser.add_argument("--result-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--directory-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--discard-normal", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.move_ms <= 3000 or args.device < 0 or not 0 <= args.a_after <= 120 or not 0 <= args.delay <= 120 or not 0.1 <= args.duration <= 60 or not 0.1 <= args.interval <= 60:
        parser.error("指定された値が範囲外です。")
    try:
        from title.BDSP.pokemon.arceus.classify import classify_directory
        with OpenCVCapture(args.device) as capture:
            capture.read()
            with SerialController(args.port) as controller:
                result = encounter(controller, capture, classify_directory, args.output, args.move_ms, args.a_after,
                                   args.delay, args.duration, args.interval)
        if args.discard_normal and result.classification == "normal":
            shutil.rmtree(result.directory)
        if args.result_file:
            args.result_file.write_text(result.classification, encoding="ascii")
        if args.directory_file:
            args.directory_file.write_text(str(result.directory), encoding="utf-8")
    except (OSError, RuntimeError, ImportError, ValueError) as exc:
        sys.exit(f"エラー: {exc}")
    except KeyboardInterrupt:
        print("中止しました。")


if __name__ == "__main__":
    main()
