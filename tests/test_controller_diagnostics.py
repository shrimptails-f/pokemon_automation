import pytest

from automation.adapters.controller_protocol import decode_frame, encode_frame
from tools.controller_diagnostics import read_diagnostics


class Port:
    def __init__(self, result):
        self.result = result
        self.requests = []
        self.frames = []
        self.response = b''

    def write(self, frame):
        self.frames.append(frame)
        request = decode_frame(frame.lstrip(b'\n')).split(',')
        self.requests.append(request)
        self.response = encode_frame(','.join(request + [self.result]))

    def readline(self):
        response, self.response = self.response, b''
        return response


def test_read_diagnostics_does_not_create_session_or_operate_controller():
    port = Port('17:2:16:3:4:5:6:7:42:9:DONE')
    assert read_diagnostics(port) == (17, 2, 16, 3, 4, 5, 6, 7, 42, 9, 'DONE')
    assert len(port.requests) == 1
    assert port.requests[0][3] == 'DIAG'
    assert port.frames[0].startswith(b'\n2,')


def test_read_diagnostics_rejects_invalid_snapshot():
    with pytest.raises(ValueError, match='形式'):
        read_diagnostics(Port('bad'))
