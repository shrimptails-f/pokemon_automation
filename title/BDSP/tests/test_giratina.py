import tempfile
from pathlib import Path

import cv2
import numpy as np

from title.BDSP.pokemon.giratina.classify import classify_directory, classify_frame


def test_reference_images():
    base = Path(__file__).resolve().parent / 'fixtures' / 'giratina'
    assert classify_frame(base / 'normal.png')[0] == 'normal'
    assert classify_frame(base / 'unknown.png')[0] == 'unknown'
    assert classify_frame(base / 'shiny_reference.png')[0] == 'shiny_candidate'


def test_directory_requires_two_normal_frames_and_prioritizes_shiny(tmp_path, monkeypatch):
    from title.BDSP.pokemon.giratina import classify as module

    states = {}
    monkeypatch.setattr(module, 'classify_frame', lambda path: (states[path.name], 0, 0))
    for i, state in enumerate(('normal', 'normal', 'shiny_candidate')):
        path = tmp_path / f'frame_{i:03d}_{9 + i * .1:.3f}s.png'
        path.touch()
        states[path.name] = state
        expected = ('unknown', 'normal', 'shiny_candidate')[i]
        assert classify_directory(tmp_path)[0] == expected


def test_directory_does_not_reset_on_ambiguous_cyan(tmp_path, monkeypatch):
    from title.BDSP.pokemon.giratina import classify as module

    for i in range(3):
        (tmp_path / f'frame_{i:03d}_{9 + i * .1:.3f}s.png').touch()
    monkeypatch.setattr(module, 'classify_frame', lambda p: ('unknown', 0, .1) if '002' in p.name else ('normal', .2, 0))
    monkeypatch.setattr(module, 'is_sendout', lambda p: False)
    assert classify_directory(tmp_path)[0] == 'unknown'
    monkeypatch.setattr(module, 'is_sendout', lambda p: True)
    assert classify_directory(tmp_path)[0] == 'normal'


def test_missing_or_blank_frames_are_unknown():
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        assert classify_directory(directory)[0] == 'unknown'
        for i, t in enumerate((9.0, 9.5)):
            cv2.imwrite(str(directory / f'frame_{i:03d}_{t:.3f}s.png'), np.zeros((480, 640, 3), dtype=np.uint8))
        assert classify_directory(directory)[0] == 'unknown'


def test_encounter_saves_24_frames_in_requested_window(tmp_path, monkeypatch):
    from title.BDSP.pokemon.giratina import encounter as module

    class Clock:
        elapsed = 0.0
        def __call__(self):
            self.elapsed += .01
            return self.elapsed

    class Capture:
        def __init__(self):
            self.paths = []
        def read(self):
            return object()
        def save(self, frame, path):
            self.paths.append(path)

    class Controller:
        def send(self, command):
            assert command == 'A'

    capture = Capture()
    monkeypatch.setattr(module, 'classify_directory', lambda directory: ('unknown', []))
    module.encounter(Controller(), capture, tmp_path, clock=Clock(), sleep=lambda _: None)
    timestamps = [float(path.stem.rsplit('_', 1)[1][:-1]) for path in capture.paths]
    assert len(timestamps) == 24
    assert all(8.2 <= t < 10.5 for t in timestamps)
