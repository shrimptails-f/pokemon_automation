"""Capture a Giratina encounter for human review."""
import math
import csv
import time
from datetime import datetime

from automation.adapters.encounter_video import EncounterVideo
from title.BDSP.domain.result import EncounterResult
from title.BDSP.pokemon.giratina.classify import classify_directory
from title.BDSP.pokemon.giratina.sparkle import detect_sparkle


def encounter(controller, capture, output, delay=8.2, duration=6.3, interval=2.3 / 24, a_after=3, *,
              clock=time.monotonic, sleep=time.sleep, on_video_start=None, on_capture_end=None,
              report=print, status=print):
    capture.read()
    status("映像に接続しました。")
    sleep(3)
    controller.send("A")
    sleep(a_after)
    controller.send("A")
    status("撮影中")
    start = clock()
    directory = output / datetime.now().strftime("giratina_%Y%m%d_%H%M%S_%f")
    directory.mkdir(parents=True, exist_ok=False)
    count = 0
    target_count = math.ceil(duration / interval - 1e-9)
    video = EncounterVideo(directory / 'encounter.mp4')
    try:
        while count < target_count:
            frame = capture.read()
            elapsed = clock() - start
            if elapsed >= delay + duration:
                raise RuntimeError(f"撮影時間内に必要な {target_count} 枚を保存できませんでした（{count} 枚）。")
            if video.first_time is None and on_video_start is not None:
                on_video_start()
            video.add(frame, elapsed)
            if elapsed >= delay + count * interval:
                capture.save(frame, directory / f"frame_{count:03d}_{elapsed:.3f}s.png")
                count += 1
    finally:
        video.close()
        if on_capture_end is not None:
            on_capture_end()
    status("画像判定中")
    classification, details = classify_directory(directory)
    sparkle, diagnostics = detect_sparkle(directory)
    with (directory / 'sparkle_diagnostics.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(('seconds', 'bright_components', 'bright_pixels', 'flash_candidate'))
        writer.writerows(diagnostics)
    sparkle_status = '判定不能（セリフ未検出・撮影不足・画面切替）' if sparkle is None else ('あり' if sparkle else 'なし')
    report(f"色判定: {classification}、発光候補: {sparkle_status} "
          f"（{len(diagnostics)} フレーム比較）")
    if sparkle:
        classification = 'shiny_candidate'
    elif sparkle is None and classification == 'normal':
        classification = 'unknown'
    report(f"{count} 枚保存しました: {directory}。判定: {classification}（色判定対象 {len(details)} 枚）")
    return EncounterResult(classification, directory)
