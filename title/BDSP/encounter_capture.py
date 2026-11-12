"""Move forward once and save a short sequence of capture frames."""
import argparse
from datetime import datetime
from pathlib import Path
import sys
import time

try:
    import cv2
    import serial
except ImportError:
    sys.exit("必要なライブラリ: python -m pip install pyserial opencv-python")


def main():
    parser = argparse.ArgumentParser(description="前進して遭遇場面を撮影する")
    parser.add_argument("port", help="SH-U09C の COM ポート")
    parser.add_argument("--move-ms", required=True, type=int, help="左スティックを上に倒す時間 (1〜3000ms)")
    parser.add_argument("--device", type=int, default=0, help="キャプチャー機器の番号")
    parser.add_argument("--a-after", required=True, type=float, help="前進終了後に A を押すまでの秒数")
    parser.add_argument("--delay", type=float, default=3.0, help="A を押し終えてから撮影開始までの秒数")
    parser.add_argument("--duration", type=float, default=5.0, help="撮影を続ける秒数")
    parser.add_argument("--interval", type=float, default=0.5, help="画像を保存する間隔（秒）")
    parser.add_argument("--output", type=Path, default=Path.home() / "Pictures" / "BDSP-captures")
    parser.add_argument("--result-file", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 1 <= args.move_ms <= 3000 or args.device < 0:
        parser.error("move-ms は 1〜3000、device は 0 以上にしてください")
    if not 0 <= args.a_after <= 120 or not 0 <= args.delay <= 120 or not 0.1 <= args.duration <= 60 or not 0.1 <= args.interval <= 60:
        parser.error("a-after と delay は 0〜120 秒、duration と interval は 0.1〜60 秒にしてください")

    capture = cv2.VideoCapture(args.device, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    try:
        if not capture.isOpened():
            sys.exit("キャプチャー機器を開けません。番号や他のアプリによる使用を確認してください。")
        ok, frame = capture.read()
        if not ok or frame is None:
            sys.exit("映像を取得できません。接続を確認してください。")
        with serial.Serial(args.port, 115200, timeout=5, write_timeout=2) as port:
            # Finish any partial command from a previous serial session.
            port.write(b"\n")
            time.sleep(0.5)
            port.reset_input_buffer()
            port.write(b"PING\n")
            if port.readline().strip() != b"PONG":
                sys.exit("Arduino から応答がありません。操作せず終了します。")
            print("映像と Arduino に接続しました。3 秒後に前進します。中止は Ctrl+C。", flush=True)
            time.sleep(3)
            port.write(f"STICK_UP {args.move_ms}\n".encode("ascii"))
            response = port.readline().strip()
            if response != b"OK":
                sys.exit(f"前進コマンドの応答エラー: {response!r}。撮影せず停止します。")
            print(f"前進完了。{args.a_after} 秒待って A を押します。", flush=True)
            deadline = time.monotonic() + args.a_after
            while time.monotonic() < deadline:
                ok, frame = capture.read()
                if not ok or frame is None:
                    sys.exit("映像が途切れました。A を押さずに停止します。")
            port.write(b"A\n")
            response = port.readline().strip()
            if response != b"OK":
                sys.exit(f"A の応答エラー: {response!r}。撮影せず停止します。")
            start = time.monotonic()
            run_dir = args.output / datetime.now().strftime("encounter_%Y%m%d_%H%M%S_%f")
            run_dir.mkdir(parents=True, exist_ok=False)
            next_save = args.delay
            count = 0
            print("A の入力完了。撮影を開始します。", flush=True)
            while time.monotonic() - start < args.delay + args.duration:
                ok, frame = capture.read()
                if not ok or frame is None:
                    sys.exit("映像が途切れました。停止します。")
                elapsed = time.monotonic() - start
                if elapsed >= next_save:
                    success, encoded = cv2.imencode(".png", frame)
                    if not success:
                        sys.exit("画像をエンコードできませんでした。")
                    path = run_dir / f"frame_{count:03d}_{elapsed:.3f}s.png"
                    path.write_bytes(encoded.tobytes())
                    count += 1
                    next_save = elapsed + args.interval
            print(f"{count} 枚保存しました: {run_dir}")
            from classify import classify_directory
            result, details = classify_directory(run_dir)
            labels = {"normal": "通常色の可能性", "shiny_candidate": "色違いの可能性", "unknown": "判定不能"}
            print(f"自動判定: {labels[result]}（対象 {len(details)} 枚）", flush=True)
            print("試験中の判定です。画像を必ず確認してください。", flush=True)
            if args.result_file:
                args.result_file.write_text(result, encoding="ascii")
    except (OSError, serial.SerialException) as exc:
        sys.exit(f"エラー: {exc}")
    except KeyboardInterrupt:
        print("中止しました。")
    finally:
        capture.release()


if __name__ == "__main__":
    main()
