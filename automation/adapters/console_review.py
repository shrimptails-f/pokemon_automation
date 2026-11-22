import logging
import shutil
import sys
import unicodedata


status_log = logging.getLogger("bdsp.status")


class ConsoleReview:
    def should_reset(self, result):
        prompt = f"\n{result.classification}（{result.directory}）を確認し、通常色なら reset、停止するなら Enter: "
        return input(prompt).strip().lower() == "reset"


class ConsoleStatus:
    def update(self, attempt, state):
        message = f"{attempt}回目: {state}" if attempt else state
        status_log.info(message, extra={"attempt": attempt})


class TerminalStatus(logging.Handler):
    """Display the latest state on one line, including the current attempt."""
    def __init__(self):
        super().__init__()
        self.attempt = 0
        self.width = 0

    def emit(self, record):
        self.attempt = getattr(record, "attempt", self.attempt)
        prefix = f"{self.attempt}回目: " if self.attempt and not hasattr(record, "attempt") else ""
        message = prefix + record.getMessage()
        if not sys.stdout.isatty():
            print(message, flush=True)
            return
        columns = max(1, shutil.get_terminal_size().columns - 1)
        width = 0
        for index, char in enumerate(message):
            size = 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
            if width + size > columns:
                message = message[:index]
                break
            width += size
        padding = " " * max(0, min(self.width, columns) - width)
        print("\r" + message + padding, end="", flush=True)
        self.width = width

    def finish(self):
        if self.width:
            print(flush=True)
