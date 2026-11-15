import pytest

from automation.adapters.controller_protocol import decode_frame, encode_frame


def test_crc_known_vector():
    assert encode_frame("123456789") == b"123456789,29B1\n"
    assert decode_frame(b"123456789,29B1\n") == "123456789"


@pytest.mark.parametrize("frame", [b"123456788,29B1\n", b"123456789,29B1", b"x,0000\n", b"\n", b"x\n,0000\n", b"x" * 128 + b",0000\n"])
def test_rejects_invalid_frames(frame):
    with pytest.raises(ValueError):
        decode_frame(frame)
