"""Preview a Windows capture device and save individual frames."""
import argparse
from datetime import datetime
from pathlib import Path
import sys

try:
    import cv2
except ImportError:
    sys.exit("OpenCV が必要です: python -m pip install opencv-python")


def main():
    parser = argparse.ArgumentParser(description="キャプチャー映像の確認")
    parser.add_argument("--device", type=int, default=0, help="映像デバイス番号 (既定: 0)")
    parser.add_argument("--output", type=Path, default=Path.home() / "Pictures" / "BDSP-captures",
                        help="画像の保存先")
    args = parser.parse_args()
    if args.device < 0:
        parser.error("デバイス番号は 0 以上にしてください")

    capture = cv2.VideoCapture(args.device, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)
    try:
        if not capture.isOpened():
            sys.exit(f"デバイス {args.device} を開けません。番号や他のアプリによる使用を確認してください。")
        print("映像ウィンドウを選択して S: 画像を保存、Q または Esc: 終了")
        while True:
            ok, frame = capture.read()
            if not ok or frame is None:
                sys.exit("映像を取得できません。接続と Switch の映像出力を確認してください。")
            height, width = frame.shape[:2]
            cv2.imshow("BDSP capture preview - S: save / Q: quit", frame)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), ord("Q"), 27):
                break
            if key in (ord("s"), ord("S")):
                args.output.mkdir(parents=True, exist_ok=True)
                path = args.output / (datetime.now().strftime("capture_%Y%m%d_%H%M%S_%f") + ".png")
                # imencode + write_bytes supports Windows paths containing Japanese characters.
                success, encoded = cv2.imencode(".png", frame)
                if not success:
                    sys.exit("画像をエンコードできませんでした。")
                path.write_bytes(encoded.tobytes())
                print(f"保存: {path} ({width}x{height})", flush=True)
            if cv2.getWindowProperty("BDSP capture preview - S: save / Q: quit", cv2.WND_PROP_VISIBLE) < 1:
                break
    except OSError as exc:
        sys.exit(f"画像の保存に失敗しました: {exc}")
    finally:
        capture.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
