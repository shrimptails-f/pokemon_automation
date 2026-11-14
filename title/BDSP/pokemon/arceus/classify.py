"""Experimental color check; it never controls or resets the game."""
import argparse
from pathlib import Path
import re
import sys

import cv2
import numpy as np

FRAME = re.compile(r"^frame_\d+_([\d.]+)s\.png$")


def classify_frame(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    frame = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if frame is None:
        raise ValueError(f"画像を読み込めません: {path}")
    frame = cv2.resize(frame, (640, 480), interpolation=cv2.INTER_AREA)
    b, g, r = cv2.split(frame)
    face = (np.maximum(np.maximum(r[110:150, 285:330], g[110:150, 285:330]), b[110:150, 285:330]) < 120).mean()
    r, g, b = (channel[194:232, 294:326].astype(np.float32) for channel in (r, g, b))
    white = ((np.minimum(np.minimum(r, g), b) > 110) &
             (np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b) < 24)).mean()
    yellow = ((r > 120) & (g > 110) & (b < g * .8) & (r > b * 1.25)).mean()
    if face < .45:
        return "unknown", white, yellow, face
    if white > .85 and yellow < .05:
        return "normal", white, yellow, face
    if yellow > .65 and white < .10:
        return "shiny_candidate", white, yellow, face
    return "unknown", white, yellow, face


def classify_directory(directory):
    paths = []
    for path in sorted(directory.glob("frame_*.png")):
        match = FRAME.match(path.name)
        if match and 5.0 <= float(match.group(1)) <= 5.4:
            paths.append(path)
    if len(paths) < 2:
        return "unknown", []
    results = [(path, *classify_frame(path)) for path in paths]
    states = [item[1] for item in results]
    if all(state == "normal" for state in states):
        return "normal", results
    if any(state == "shiny_candidate" for state in states):
        return "shiny_candidate", results
    return "unknown", results


def main():
    parser = argparse.ArgumentParser(description="遭遇画像の色を試験的に判定")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    try:
        result, details = classify_directory(args.directory)
        for path, status, white, yellow, face in details:
            print(f"{path.name}: {status} (白={white:.2f}, 黄={yellow:.2f}, 顔={face:.2f})")
        print("判定:", {"normal": "通常色の可能性", "shiny_candidate": "色違いの可能性", "unknown": "判定不能"}[result])
        print("試験中の判定です。画像を必ず確認してください。")
    except (OSError, ValueError) as exc:
        sys.exit(f"判定エラー: {exc}")


if __name__ == "__main__":
    main()
