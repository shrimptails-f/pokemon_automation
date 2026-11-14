"""Compose the BDSP application and its hardware adapters."""
import argparse
import logging
from pathlib import Path
import sys
import threading

from automation.adapters.console_review import ConsoleReview, ConsoleStatus
from automation.adapters.opencv_capture import OpenCVCapture
from automation.adapters.serial_controller import SerialController
from title.BDSP.application.loop import run_loop
from title.BDSP.gameplay.reset import reset
from title.BDSP.pokemon.arceus.encounter import encounter


def main():
    parser = argparse.ArgumentParser(description="画像を確認しながら遭遇を繰り返す")
    parser.add_argument("port")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--move-ms", type=int, required=True)
    parser.add_argument("--a-after", type=float, required=True)
    parser.add_argument("--auto-reset", action="store_true")
    parser.add_argument("--discord", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Arduino の通信ログを表示する")
    parser.add_argument("--reset-first", action="store_true")
    parser.add_argument("--output", type=Path, default=Path.home() / "Pictures" / "BDSP-captures")
    args = parser.parse_args()
    if args.debug:
        serial_logger = logging.getLogger("automation.adapters.serial_controller")
        serial_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [Arduino] %(message)s", datefmt="%H:%M:%S"))
        serial_logger.addHandler(handler)
        serial_logger.propagate = False
    if not 1 <= args.move_ms <= 3000 or not 0 <= args.a_after <= 120 or args.device < 0:
        parser.error("move-ms は 1〜3000、a-after は 0〜120、device は 0 以上にしてください")
    try:
        from title.BDSP.pokemon.arceus.classify import classify_directory
        stop = threading.Event()

        def check_stop():
            if stop.is_set():
                raise InterruptedError("中止しました。")

        def sleep(seconds):
            if stop.wait(seconds):
                check_stop()

        class StoppableController:
            def __init__(self, controller):
                self.controller = controller

            def send(self, command):
                check_stop()
                self.controller.send(command)

        class StoppableCapture:
            def __init__(self, capture):
                self.capture = capture

            def read(self):
                check_stop()
                return self.capture.read()

            def save(self, frame, path):
                check_stop()
                self.capture.save(frame, path)

        def do_encounter():
            with OpenCVCapture(args.device) as capture:
                capture.read()
                return encounter(stoppable_controller, StoppableCapture(capture), classify_directory,
                                 args.output, args.move_ms, args.a_after, sleep=sleep)

        def do_reset():
            reset(stoppable_controller, sleep=sleep)

        with SerialController(args.port) as controller:
            stoppable_controller = StoppableController(controller)
            if args.discord:
                from automation.adapters.discord.review import main as discord_main
                discord_main(args, do_encounter, do_reset, run_loop, stop,
                             legacy_env=Path(__file__).with_name(".env"))
            else:
                run_loop(do_encounter, do_reset, ConsoleReview(), ConsoleStatus(),
                         auto_reset=args.auto_reset, reset_first=args.reset_first)
    except (OSError, RuntimeError, ImportError, ValueError) as exc:
        logging.getLogger(__name__).exception("操作中にエラーが発生しました")
        sys.exit(f"操作を停止しました: {exc}")
    except (KeyboardInterrupt, EOFError):
        print("\n停止しました。")


if __name__ == "__main__":
    main()
