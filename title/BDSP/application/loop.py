import shutil
from typing import Callable

from automation.ports.review import Review
from automation.ports.status import Status
from title.BDSP.domain.result import EncounterResult


def run_loop(encounter: Callable[[], EncounterResult], reset: Callable[[], None],
             review: Review, status: Status, *, auto_reset=False, reset_first=False):
    if reset_first:
        status.update(0, "開始前のリセット中")
        reset()
    attempt = 0
    while True:
        attempt += 1
        status.update(attempt, "遭遇・撮影中")
        result = encounter()
        if result.classification not in ("normal", "unknown", "shiny_candidate"):
            raise RuntimeError("不明な判定結果です。")
        if auto_reset and result.classification == "normal":
            shutil.rmtree(result.directory)
        elif not review.should_reset(result):
            status.update(attempt, "停止")
            return
        status.update(attempt, "リセット中")
        reset()
