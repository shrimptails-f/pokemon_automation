"""Create a video showing per-frame sparkle detector scores."""
import argparse
import csv
import tempfile
from pathlib import Path

import cv2

from title.BDSP.pokemon.giratina.sparkle import detect_sparkle


def main():
    parser = argparse.ArgumentParser(description='発光判定の確認動画を作成する')
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    capture = cv2.VideoCapture(str(args.input))
    fps = capture.get(cv2.CAP_PROP_FPS)
    if not capture.isOpened() or fps <= 0:
        raise ValueError('入力動画を開けません。')
    step = max(1, round(fps / 15))
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        i = 0
        saved = 0
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            if i % step == 0:
                path = directory / f'frame_{saved:06d}_{i / fps:.3f}s.png'
                if not cv2.imwrite(str(path), frame):
                    raise OSError(f'画像を保存できません: {path}')
                saved += 1
            i += 1
        capture.release()
        candidate, diagnostics = detect_sparkle(directory)
        scores = {round(t, 3): (count, pixels, hit) for t, count, pixels, hit in diagnostics}
        writer = cv2.VideoWriter(str(args.output), cv2.VideoWriter_fourcc(*'mp4v'), fps / step, (640, 360))
        if not writer.isOpened():
            raise OSError('出力動画を作成できません。')
        try:
            for path in sorted(directory.glob('frame_*.png')):
                t = float(path.stem.rsplit('_', 1)[1][:-1])
                frame = cv2.resize(cv2.imread(str(path)), (640, 360))
                count, pixels, hit = scores.get(t, (0, 0, False))
                cv2.rectangle(frame, (100, 50), (540, 310), (255, 128, 0), 1)
                text = f'{t:.2f}s components={count} pixels={pixels} flash={hit}'
                cv2.putText(frame, text, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, .52, (0, 0, 0), 3)
                cv2.putText(frame, text, (8, 25), cv2.FONT_HERSHEY_SIMPLEX, .52, (255, 255, 255), 1)
                writer.write(frame)
        finally:
            writer.release()
        with args.output.with_suffix('.csv').open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(('seconds', 'bright_components', 'bright_pixels', 'flash_candidate'))
            writer.writerows(diagnostics)
        status = '判定不能' if candidate is None else ('あり' if candidate else 'なし')
        print(f'発光候補: {status}。確認動画: {args.output}')


if __name__ == '__main__':
    main()
