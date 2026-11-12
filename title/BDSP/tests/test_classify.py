"""Tests with captured normal images and a video reference image."""
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

BDSP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BDSP_DIR))
from classify import classify_directory, classify_frame

FIXTURES = Path(os.environ.get("BDSP_FIXTURES", BDSP_DIR / "tests" / "fixtures"))


class ClassifierImageTests(unittest.TestCase):
    def setUp(self):
        self.normal_dirs = sorted((FIXTURES / "normal_runs").glob("encounter_*"))
        self.normal_dirs.append(FIXTURES / "normal_additional")
        self.shiny = FIXTURES / "shiny_reference" / "アルセウス色.png"
        self.white = FIXTURES / "transition" / "frame_007_6.573s.png"
        if len(self.normal_dirs) != 4 or not self.shiny.is_file() or not self.white.is_file():
            self.fail(f"テスト画像が不足しています: {FIXTURES} (normal_runs の3回分、normal_additional、transition、shiny_reference が必要)")

    def test_normal_encounters(self):
        for directory in self.normal_dirs:
            with self.subTest(directory=directory):
                result, frames = classify_directory(directory)
                self.assertGreaterEqual(len(frames), 2)
                self.assertEqual(result, "normal")

    def test_reference_shiny_frame(self):
        self.assertEqual(classify_frame(self.shiny)[0], "shiny_candidate")

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


if __name__ == "__main__":
    unittest.main()
