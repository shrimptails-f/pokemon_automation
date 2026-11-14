import time
from automation.ports.controller import Controller


def reset(controller: Controller, *, sleep=time.sleep):
    for button in ("HOME", "X", "A", "A", "A"):
        controller.send(button)
        sleep(2)
    sleep(12.5)
    for delay in (2, 2, 7):
        controller.send("A")
        sleep(delay)
