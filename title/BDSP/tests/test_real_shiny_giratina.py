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


def _args(**values):
    from argparse import Namespace
    base = dict(pokemon='giratina', audio_reference=None, audio_start=None, audio_end=None,
                audio_device=None, audio_threshold=.5)
    return Namespace(**{**base, **values})


def test_bundled_sound_is_used_when_only_device_is_given():
    from title.BDSP.main import SHINY_SOUND, resolve_audio

    assert SHINY_SOUND == SOUND
    args = _args(audio_device=0)
    assert resolve_audio(args)
    assert (args.audio_reference, args.audio_start, args.audio_end) == (SOUND, 0.0, None)


def test_explicit_reference_keeps_previous_defaults():
    from title.BDSP.main import resolve_audio

    args = _args(audio_reference=Path('ref.mp4'), audio_device=0)
    assert resolve_audio(args)
    assert (args.audio_start, args.audio_end) == (12.0, 14.0)
    assert not resolve_audio(_args(audio_reference=Path('ref.mp4'), audio_start=3, audio_end=2))


def test_audio_is_disabled_without_device_or_for_other_pokemon():
    from title.BDSP.main import resolve_audio

    args = _args()
    assert resolve_audio(args) and args.audio_reference is None
    args = _args(pokemon='arceus', audio_device=0)
    assert resolve_audio(args) and args.audio_reference is None
    assert not resolve_audio(_args(pokemon='arceus', audio_reference=Path('ref.mp4')))


def test_real_shiny_sparkle_after_camera_cut_is_candidate():
    from title.BDSP.pokemon.giratina.sparkle import detect_sparkle

    candidate, diagnostics = detect_sparkle(FIXTURE)
    assert candidate is True
    assert [round(t, 3) for t, _, _, hit in diagnostics if hit] == [12.624, 12.707]


def test_ball_flash_while_sendout_dialogue_fades_in_is_not_candidate():
    from title.BDSP.pokemon.giratina.sparkle import detect_sparkle

    assert detect_sparkle(FIXTURE.parent / 'normal_sendout_fade')[0] is False
