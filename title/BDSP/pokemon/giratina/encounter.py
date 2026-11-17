"""Capture a Giratina encounter for human review."""
import math
import time
from datetime import datetime

from title.BDSP.domain.result import EncounterResult
from title.BDSP.pokemon.giratina.classify import classify_directory


def encounter(controller, capture, output, delay=8.2, duration=2.3, interval=2.3 / 24, a_after=3, *,
              clock=time.monotonic, sleep=time.sleep):
    capture.read()
    print("映像を確認しました。3 秒後に A を押します。中止は Ctrl+C。", flush=True)
    sleep(3)
    controller.send("A")
    sleep(a_after)
    controller.send("A")
    start = clock()
    directory = output / datetime.now().strftime("giratina_%Y%m%d_%H%M%S_%f")
    directory.mkdir(parents=True, exist_ok=False)
    count = 0
    target_count = math.ceil(duration / interval - 1e-9)
    while count < target_count:
        frame = capture.read()
        elapsed = clock() - start
        if elapsed >= delay + duration:
            raise RuntimeError(f"撮影時間内に必要な {target_count} 枚を保存できませんでした（{count} 枚）。")
        if elapsed >= delay + count * interval:
            capture.save(frame, directory / f"frame_{count:03d}_{elapsed:.3f}s.png")
            count += 1
    classification, details = classify_directory(directory)
    print(f"{count} 枚保存しました: {directory}。判定: {classification}（対象 {len(details)} 枚）", flush=True)
    return EncounterResult(classification, directory)
