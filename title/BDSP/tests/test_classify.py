"""Tests with captured normal images and a video reference image."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

import pytest

BDSP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BDSP_DIR.parents[1]))
from title.BDSP.pokemon.arceus.classify import classify_directory, classify_frame

FIXTURES = Path(os.environ.get("BDSP_FIXTURES", BDSP_DIR / "tests" / "fixtures"))


class ClassifierImageTests(unittest.TestCase):
    def setUp(self):
        self.normal_dirs = sorted((FIXTURES / "normal_runs").glob("encounter_*"))
        self.normal_dirs.extend([FIXTURES / "normal_additional", FIXTURES / "normal_delayed"])
        self.shiny = FIXTURES / "shiny_reference" / "アルセウス色.png"
        self.white = FIXTURES / "transition" / "frame_007_6.573s.png"
        if len(self.normal_dirs) != 5 or not self.shiny.is_file() or not self.white.is_file():
            self.fail(f"テスト画像が不足しています: {FIXTURES} (normal_runs の3回分、normal_additional、normal_delayed、transition、shiny_reference が必要)")

    def test_reference_shiny_frame(self):
        self.assertEqual(classify_frame(self.shiny)[0], "shiny_candidate")

    def test_captured_shiny_encounter(self):
        directory = FIXTURES / "shiny_capture"
        result, frames = classify_directory(directory)
        self.assertGreaterEqual(len(frames), 2)
        self.assertEqual(result, "shiny_candidate")
        self.assertTrue(all(frame[1] == "shiny_candidate" for frame in frames))

    def test_white_transition_is_unknown(self):
        self.assertEqual(classify_frame(self.white)[0], "unknown")

    def test_insufficient_frames_do_not_trigger_normal(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            source = next(self.normal_dirs[0].glob("frame_002_*.png"))
            shutil.copyfile(source, directory / "frame_000_5.000s.png")
            self.assertEqual(classify_directory(directory)[0], "unknown")

    def test_shiny_frame_prevents_normal_in_mixed_sequence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            normal = next(self.normal_dirs[0].glob("frame_002_*.png"))
            shutil.copyfile(normal, directory / "frame_000_5.000s.png")
            shutil.copyfile(self.shiny, directory / "frame_001_5.250s.png")
            self.assertEqual(classify_directory(directory)[0], "shiny_candidate")

    def test_white_frame_prevents_normal_in_mixed_sequence(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            normal = next(self.normal_dirs[0].glob("frame_002_*.png"))
            shutil.copyfile(normal, directory / "frame_000_5.000s.png")
            shutil.copyfile(self.white, directory / "frame_001_5.250s.png")
            self.assertEqual(classify_directory(directory)[0], "unknown")


@pytest.mark.parametrize("directory", [
    pytest.param(FIXTURES / "normal_runs" / name, id=name)
    for name in (
        "encounter_20261112_232109_229496",
        "encounter_20261112_232226_555545",
        "encounter_20261112_232341_820556",
    )
] + [
    pytest.param(FIXTURES / name, id=name)
    for name in ("normal_additional", "normal_delayed")
])
def test_normal_encounter(directory):
    result, frames = classify_directory(directory)
    assert len(frames) >= 2
    assert result == "normal"


if __name__ == "__main__":
    unittest.main()
