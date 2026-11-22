import cv2
import numpy as np

from automation.adapters.encounter_video import EncounterVideo
from title.BDSP.pokemon.giratina.shiny_audio import RATE, add_audio_to_video, read_audio


def test_video_and_audio_are_saved_in_unicode_path(tmp_path):
    path = tmp_path / '記録' / 'encounter.mp4'
    path.parent.mkdir()
    video = EncounterVideo(path)
    for i in range(10):
        video.add(np.full((64, 64, 3), i * 20, dtype=np.uint8), i / 10)
    video.close()
    capture = cv2.VideoCapture(str(path))
    assert capture.isOpened()
    assert int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 10
    capture.release()

    times = np.arange(RATE * 2) / RATE
    samples = .2 * np.sin(2 * np.pi * 440 * times)
    add_audio_to_video(path, samples, .3)
    assert np.max(np.abs(read_audio(path))) > .1
