from pathlib import Path
from typing import Protocol


class ReviewResult(Protocol):
    @property
    def classification(self) -> str: ...
    @property
    def directory(self) -> Path: ...


class Review(Protocol):
    def should_reset(self, result: ReviewResult) -> bool: ...
