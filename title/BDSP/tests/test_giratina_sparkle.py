import cv2
import numpy as np

from title.BDSP.pokemon.giratina.classify import TEMPLATES
from title.BDSP.pokemon.giratina.sparkle import detect_sparkle


def make_frames(directory, *, flash_at=(), dialogue=True, count=27, cut_at=None, sendout=False):
    template = cv2.imread(str(TEMPLATES / 'dialog_encounter.png'))
    sendout_template = cv2.imread(str(TEMPLATES / 'dialog_sendout.png'))
    for i in range(count):
        image = np.full((480, 640, 3), 180 if cut_at is not None and i >= cut_at else 0, dtype=np.uint8)
        if dialogue and i < 5:
            image[400:428, 50:250] = template
        if sendout and cut_at is not None and i >= cut_at + 2:
            image[400:428, 50:250] = sendout_template
        if i in flash_at:
            for y in range(120, 320, 40):
                for x in range(140, 500, 55):
                    cv2.circle(image, (x, y), 7, (255, 255, 255), -1)
        cv2.imwrite(str(directory / f'frame_{i:03d}_{i / 10:.3f}s.png'), image)


def test_only_post_dialogue_flashes_are_candidates(tmp_path):
    make_frames(tmp_path, flash_at=(2, 3, 7, 8))
    candidate, diagnostics = detect_sparkle(tmp_path)
    assert candidate is True
    assert all(.4 < row[0] <= 2.4 for row in diagnostics)


def test_flashes_before_dialogue_ends_do_not_count(tmp_path):
    make_frames(tmp_path, flash_at=(2, 3))
    assert detect_sparkle(tmp_path)[0] is False


def test_missing_dialogue_or_incomplete_window_is_unknown(tmp_path):
    make_frames(tmp_path, dialogue=False)
    assert detect_sparkle(tmp_path)[0] is None
    for path in tmp_path.glob('*.png'):
        path.unlink()
    make_frames(tmp_path, count=12)
    assert detect_sparkle(tmp_path)[0] is None


def test_early_cut_requires_sendout_confirmation(tmp_path):
    make_frames(tmp_path, cut_at=9, sendout=True)
    assert detect_sparkle(tmp_path)[0] is False
    make_frames(tmp_path, cut_at=9, sendout=False)
    assert detect_sparkle(tmp_path)[0] is None


def test_early_cut_cannot_hide_flash_candidate(tmp_path):
    make_frames(tmp_path, flash_at=(6, 7), cut_at=9, sendout=True)
    assert detect_sparkle(tmp_path)[0] is True


def test_flash_after_cut_to_wider_shot_is_candidate(tmp_path):
    make_frames(tmp_path, flash_at=(12, 13), cut_at=9)
    assert detect_sparkle(tmp_path)[0] is True


def test_sendout_ball_flash_is_not_candidate(tmp_path):
    make_frames(tmp_path, flash_at=(11, 12), cut_at=9, sendout=True)
    assert detect_sparkle(tmp_path)[0] is False
