import tempfile
import unittest
from pathlib import Path

from title.BDSP.application.loop import run_loop
from title.BDSP.domain.result import EncounterResult
from title.BDSP.gameplay.reset import reset


class Ports:
    def __init__(self, choice=False):
        self.choice = choice
        self.states = []
        self.reviews = []

    def update(self, attempt, state):
        self.states.append((attempt, state))

    def should_reset(self, result):
        self.reviews.append(result)
        return self.choice


class LoopTests(unittest.TestCase):
    def test_auto_normal_resets_then_shiny_requests_review(self):
        with tempfile.TemporaryDirectory() as temp:
            normal = Path(temp) / 'normal'
            normal.mkdir()
            shiny = Path(temp) / 'shiny'
            shiny.mkdir()
            results = iter([EncounterResult('normal', normal), EncounterResult('shiny_candidate', shiny)])
            resets = []
            ports = Ports()
            run_loop(lambda: next(results), lambda: resets.append(True), ports, ports, auto_reset=True)
            self.assertEqual(resets, [True])
            self.assertFalse(normal.exists())
            self.assertTrue(shiny.exists())
            self.assertEqual(ports.reviews, [EncounterResult('shiny_candidate', shiny)])

    def test_shiny_review_can_resume(self):
        ports = Ports(choice=True)
        resets = []
        shiny = EncounterResult('shiny_candidate', Path('shiny'))
        unknown = EncounterResult('unknown', Path('unknown'))
        results = iter([shiny, unknown])
        def reset_once():
            resets.append(True)
            ports.choice = False
        run_loop(lambda: next(results), reset_once, ports, ports, auto_reset=True)
        self.assertEqual(ports.reviews, [shiny, unknown])
        self.assertEqual(resets, [True])

    def test_unknown_requires_review(self):
        ports = Ports()
        resets = []
        result = EncounterResult('unknown', Path('unknown'))
        run_loop(lambda: result, lambda: resets.append(True), ports, ports, auto_reset=True)
        self.assertEqual(ports.reviews, [result])
        self.assertEqual(resets, [])

    def test_reset_stops_on_controller_failure(self):
        class Controller:
            def __init__(self): self.commands = []
            def send(self, command):
                self.commands.append(command)
                if command == 'X': raise RuntimeError('failure')
        controller = Controller()
        with self.assertRaises(RuntimeError):
            reset(controller, sleep=lambda _: None)
        self.assertEqual(controller.commands, ['HOME', 'X'])


if __name__ == '__main__':
    unittest.main()
