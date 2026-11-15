import serial
import pytest

from automation.adapters.serial_controller import SerialController
from automation.adapters.controller_protocol import decode_frame, encode_frame


class FakePort:
    def __init__(self):
        self.responses = []
        self.requests = []
        self.closed = False
        self.drop_set = False

    def write(self, data):
        if data == b'\n':
            return
        fields = decode_frame(data).split(',')
        self.requests.append(fields)
        op = fields[3]
        if op == 'SET' and self.drop_set:
            self.drop_set = False
            return
        result = 'APPLIED' if op == 'SET' else 'ACTIVE'
        self.responses.append(encode_frame(','.join(fields[:4] + [result])))

    def readline(self):
        return self.responses.pop(0) if self.responses else b''

    def reset_input_buffer(self):
        self.responses.clear()

    def close(self):
        self.closed = True


def test_press_and_release_and_retry_same_request(monkeypatch):
    port = FakePort()
    monkeypatch.setattr(serial, 'Serial', lambda *a, **kw: port)
    monkeypatch.setattr('automation.adapters.serial_controller.time.sleep', lambda _: None)
    with SerialController('COM8') as controller:
        port.drop_set = True
        controller.send('A')
    sets = [r for r in port.requests if r[3] == 'SET']
    assert sets[0] == sets[1]
    assert sets[0][4] == '4'
    assert sets[2][4] == '0'
    assert port.closed


def test_rejects_out_of_range_state():
    with pytest.raises(ValueError):
        SerialController('COM8').set_state(hat=9)


def test_corrupt_response_is_not_accepted(monkeypatch):
    port = FakePort()
    port.readline = lambda: b'bad,0000\n'
    monkeypatch.setattr(serial, 'Serial', lambda *a, **kw: port)
    monkeypatch.setattr('automation.adapters.serial_controller.time.sleep', lambda _: None)
    with pytest.raises(TimeoutError):
        with SerialController('COM8'):
            pass
    assert port.closed
