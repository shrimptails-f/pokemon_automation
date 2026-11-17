import numpy as np
import pytest

from title.BDSP.pokemon.giratina.shiny_audio import RATE, correlate


def test_finds_reference_after_gain_and_offset():
    rng = np.random.default_rng(7)
    template = rng.normal(size=2000)
    recording = rng.normal(scale=0.02, size=10000)
    recording[4000:6000] = template * 0.3 + 0.1
    score, at = correlate(recording, template)
    assert score > 0.999
    assert at == pytest.approx(4000 / RATE)


def test_rejects_silent_reference_and_short_recording():
    with pytest.raises(ValueError):
        correlate(np.ones(100), np.zeros(20))
    with pytest.raises(ValueError):
        correlate(np.ones(10), np.arange(20))
