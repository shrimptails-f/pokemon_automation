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
    parser.add_argument("--pokemon", choices=("arceus", "giratina"), default="arceus")
    parser.add_argument("--move-ms", type=int)
    parser.add_argument("--a-after", type=float)
    parser.add_argument("--capture-delay", type=float, default=8.2)
    parser.add_argument("--capture-duration", type=float, default=6.3)
    parser.add_argument("--capture-interval", type=float, default=2.3 / 24)
    parser.add_argument("--auto-reset", action="store_true")
    parser.add_argument("--discord", action="store_true")
    parser.add_argument("--debug", action="store_true", help="Arduino の通信ログを表示する")
    parser.add_argument("--reset-first", action="store_true")
    parser.add_argument("--output", type=Path, default=Path.home() / "Pictures" / "BDSP-captures")
    parser.add_argument("--audio-reference", type=Path, help="色違い音声の参照動画または音声")
    parser.add_argument("--audio-start", type=float, default=12.0)
    parser.add_argument("--audio-end", type=float, default=14.0)
    parser.add_argument("--audio-device", type=int, help="録音入力デバイス番号")
    parser.add_argument("--audio-threshold", type=float, default=0.7)
    args = parser.parse_args()
    if args.audio_reference and (args.pokemon != 'giratina' or args.audio_start < 0 or args.audio_end <= args.audio_start or not 0 < args.audio_threshold <= 1):
        parser.error('音声判定はギラティナのみ対応し、参照時間としきい値を正しく指定してください。')
    if args.debug:
        serial_logger = logging.getLogger("automation.adapters.serial_controller")
        serial_logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(asctime)s [Arduino] %(message)s", datefmt="%H:%M:%S"))
        serial_logger.addHandler(handler)
        serial_logger.propagate = False
    if args.device < 0 or (args.pokemon == "arceus" and (args.move_ms is None or args.a_after is None or not 1 <= args.move_ms <= 3000 or not 0 <= args.a_after <= 120)) or (args.pokemon == "giratina" and args.a_after is not None and not 0 <= args.a_after <= 120) or not 0 <= args.capture_delay <= 120 or not 0.1 <= args.capture_duration <= 120 or not 0.05 <= args.capture_interval <= 60:
        parser.error("move-ms は 1〜3000、a-after は 0〜120、device は 0 以上にしてください")
    try:
        audio_template = None
        if args.audio_reference:
            from title.BDSP.pokemon.giratina.shiny_audio import RATE, AudioRecorder, add_audio_to_video, correlate, read_audio
            audio_template = read_audio(args.audio_reference, args.audio_start, args.audio_end - args.audio_start)
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
                if args.pokemon == "giratina":
                    from title.BDSP.pokemon.giratina.encounter import encounter as giratina_encounter
                    def capture_giratina(on_video_start=None, on_capture_end=None):
                        return giratina_encounter(stoppable_controller, StoppableCapture(capture), args.output,
                                                  args.capture_delay, args.capture_duration, args.capture_interval,
                                                  args.a_after if args.a_after is not None else 3, sleep=sleep,
                                                  on_video_start=on_video_start, on_capture_end=on_capture_end)
                    if audio_template is None:
                        return capture_giratina()
                    with AudioRecorder(args.audio_device) as recorder:
                        result = capture_giratina(recorder.mark_video_start, recorder.stop)
                    samples = recorder.samples()
                    if recorder.video_started_at is None:
                        raise RuntimeError('動画の開始時刻を取得できませんでした。')
                    offset = recorder.video_started_at - recorder.started_at
                    add_audio_to_video(result.directory / 'encounter.mp4', samples, offset)
                    video_samples = samples[max(0, round(offset * RATE)):]
                    score, at = correlate(video_samples, audio_template)
                    print(f"音声相関: {score:.4f}（動画開始から {at:.2f} 秒、しきい値 {args.audio_threshold:.3f}）", flush=True)
                    if score >= args.audio_threshold:
                        from title.BDSP.domain.result import EncounterResult
                        return EncounterResult('shiny_candidate', result.directory)
                    return result
                return encounter(stoppable_controller, StoppableCapture(capture), classify_directory,
                                 args.output, args.move_ms, args.a_after, sleep=sleep)

        def do_reset():
            reset(stoppable_controller, sleep=sleep)

        with SerialController(args.port) as controller:
            print("Arduino に接続しました。", flush=True)
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
