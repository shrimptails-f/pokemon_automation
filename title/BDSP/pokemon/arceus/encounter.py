import time
from datetime import datetime

from automation.ports.capture import Capture
from automation.ports.controller import Controller
from title.BDSP.domain.result import EncounterResult


def encounter(controller: Controller, capture: Capture, classify, output, move_ms, a_after,
              delay=4.5, duration=1.5, interval=0.25, *, clock=time.monotonic, sleep=time.sleep,
              report=print, status=print):
    capture.read()  # Verify the video before moving.
    status("映像に接続しました。")
    sleep(3)
    controller.send(f"STICK_UP {move_ms}")
    deadline = clock() + a_after
    while clock() < deadline:
        capture.read()
    controller.send("A")
    status("撮影中")
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
    status("画像判定中")
    classification, details = classify(directory)
    if classification not in ("normal", "unknown", "shiny_candidate"):
        raise RuntimeError("不明な判定結果です。")
    report(f"{count} 枚保存しました: {directory}。判定: {classification}（対象 {len(details)} 枚）")
    return EncounterResult(classification, directory)
