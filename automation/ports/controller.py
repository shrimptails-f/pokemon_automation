from typing import Protocol


class Controller(Protocol):
    def send(self, command: str) -> None: ...
