from typing import Protocol


class Status(Protocol):
    def update(self, attempt: int, state: str) -> None: ...
