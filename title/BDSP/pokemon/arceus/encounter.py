import time
from datetime import datetime

from automation.ports.capture import Capture
from automation.ports.controller import Controller
from title.BDSP.domain.result import EncounterResult


def encounter(controller: Controller, capture: Capture, classify, output, move_ms, a_after,
              delay=4.5, duration=1.5, interval=0.25, *, clock=time.monotonic, sleep=time.sleep):
    capture.read()  # Verify the video before moving.
    print("映像を確認しました。3 秒後に前進します。中止は Ctrl+C。", flush=True)
    sleep(3)
    controller.send(f"STICK_UP {move_ms}")
    deadline = clock() + a_after
    while clock() < deadline:
        capture.read()
    controller.send("A")
    start = clock()
    directory = output / datetime.now().strftime("encounter_%Y%m%d_%H%M%S_%f")
    directory.mkdir(parents=True, exist_ok=False)
    next_save = delay
    count = 0
    while clock() - start < delay + duration:
        frame = capture.read()
        elapsed = clock() - start
        if elapsed >= next_save:
            capture.save(frame, directory / f"frame_{count:03d}_{elapsed:.3f}s.png")
            count += 1
            next_save = elapsed + interval
    classification, details = classify(directory)
    if classification not in ("normal", "unknown", "shiny_candidate"):
        raise RuntimeError("不明な判定結果です。")
    print(f"{count} 枚保存しました: {directory}。判定: {classification}（対象 {len(details)} 枚）", flush=True)
    return EncounterResult(classification, directory)
