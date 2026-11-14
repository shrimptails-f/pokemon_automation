from pathlib import Path
from typing import Protocol


class Capture(Protocol):
    def read(self): ...
    def save(self, frame, path: Path) -> None: ...
