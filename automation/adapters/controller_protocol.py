"""Controller protocol framing primitives.

CRC-16/CCITT-FALSE covers the ASCII payload, excluding the comma before the
four hexadecimal CRC digits and the trailing newline.
"""
import binascii
import re

MAX_LINE = 128
_CRC = re.compile(rb"[0-9A-F]{4}\Z")


def encode_frame(payload: str) -> bytes:
    data = payload.encode("ascii")
    if not data or b"\n" in data or b"\r" in data:
        raise ValueError("invalid payload")
    frame = data + b"," + f"{binascii.crc_hqx(data, 0xffff):04X}".encode() + b"\n"
    if len(frame) > MAX_LINE:
        raise ValueError("frame too long")
    return frame


def decode_frame(frame: bytes) -> str:
    if len(frame) > MAX_LINE or not frame.endswith(b"\n"):
        raise ValueError("invalid frame length or terminator")
    try:
        payload, checksum = frame[:-1].rsplit(b",", 1)
    except ValueError as exc:
        raise ValueError("missing CRC") from exc
    if not payload or b"\r" in payload or b"\n" in payload or not _CRC.fullmatch(checksum):
        raise ValueError("invalid frame")
    if binascii.crc_hqx(payload, 0xffff) != int(checksum, 16):
        raise ValueError("CRC mismatch")
    try:
        return payload.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("non-ASCII payload") from exc
