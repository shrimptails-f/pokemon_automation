from pathlib import Path

from title.BDSP.pokemon.giratina.classify import classify_directory
from title.BDSP.pokemon.giratina.shiny_audio import correlate, read_audio

BASE = Path(__file__).resolve().parents[1]
FIXTURE = BASE / 'tests' / 'fixtures' / 'giratina' / 'real_shiny'
SOUND = BASE / 'pokemon' / 'giratina' / 'templates' / 'shiny_sound.wav'


def test_real_shiny_color_is_candidate():
    assert classify_directory(FIXTURE)[0] == 'shiny_candidate'


def test_bundled_shiny_sound_matches_real_encounter():
    score, at = correlate(read_audio(FIXTURE / 'encounter.mp4'), read_audio(SOUND))
    assert score >= .9
    assert 11.5 <= at <= 13.0
