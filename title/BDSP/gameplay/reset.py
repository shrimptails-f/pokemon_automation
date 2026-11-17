import time
from automation.ports.controller import Controller


def reset(controller: Controller, *, sleep=time.sleep):
    for button, delay in (("HOME", 1.5), ("X", 1.5), ("A", 1.5), ("A", 1.5), ("A", 2)):
        controller.send(button)
        sleep(delay)
    sleep(12.5)
    for delay in (2, 2, 7):
        controller.send("A")
        sleep(delay)
