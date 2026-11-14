import tempfile
from pathlib import Path

import cv2
import numpy as np

from title.BDSP.pokemon.giratina.classify import classify_directory, classify_frame


def test_reference_images():
    base = Path(__file__).resolve().parents[1] / 'pokemon' / 'giratina'
    for name in ('1', '2', '3'):
        assert classify_directory(base / name)[0] == 'normal'
    assert classify_directory(base / '6')[0] == 'normal'
    assert classify_directory(base / '7')[0] == 'normal'
    assert classify_directory(base / 'unnokwn' / '1')[0] == 'normal'
    assert classify_directory(base / 'unnokwn' / '2')[0] == 'normal'
    assert classify_frame(base / '7' / 'frame_014_11.619s.png')[0] == 'unknown'
    for name in ('4', '5'):
        assert classify_directory(base / name)[0] == 'unknown'
    references = list((base / 'shiniy').glob('*.png'))
    assert len(references) == 3
    for path in references:
        assert classify_frame(path)[0] == 'shiny_candidate'
    assert classify_frame(base / '6' / 'frame_022_13.654s.png')[0] == 'unknown'


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
