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
        self.timed_seen = set()

    def write(self, data):
        if data == b'\n':
            return
        fields = decode_frame(data).split(',')
        self.requests.append(fields)
        op = fields[3]
        if op == 'TIMED':
            key = tuple(fields)
            result = 'DONE' if key in self.timed_seen else 'RUNNING'
            self.timed_seen.add(key)
        else:
            result = 'APPLIED' if op == 'SET' else 'ACTIVE'
        if op == 'TIMED' and self.drop_set:
            self.drop_set = False
            return
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
    timed = [r for r in port.requests if r[3] == 'TIMED']
    assert len(timed) >= 2
    assert all(r == timed[0] for r in timed)
    assert timed[0][4] == '4'
    assert timed[0][10] == '0'
    assert timed[0][-1] == '150'
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


def test_neutral_expiration_establishes_new_session():
    controller = SerialController('COM8')
    old = controller.session
    calls = []

    def request(command, expected):
        calls.append((command, controller.session))
        return {'STATUS': 'EXPIRED', 'HELLO': 'ACTIVE'}[command]

    controller._request = request
    controller._recover_neutral()
    assert calls[0] == ('STATUS', old)
    assert calls[1][0] == 'HELLO'
    assert calls[1][1] != old
    assert controller.sequence == 0


def test_other_active_session_is_not_taken_over(monkeypatch):
    from automation.adapters.serial_controller import ProtocolError
    controller = SerialController('COM8')
    calls = []

    def request(command, expected):
        calls.append(command)
        if command == 'KEEP':
            raise ProtocolError('SESSION')
        return 'ACTIVE'

    controller._request = request
    monkeypatch.setattr(controller.stopped, 'wait', lambda _: False)
    with pytest.raises(RuntimeError, match='復旧に失敗'):
        controller._recover_neutral()
    assert 'HELLO' not in calls


def test_session_rejection_checks_status_before_stopping():
    from automation.adapters.serial_controller import ProtocolError
    controller = SerialController('COM8')
    calls = []

    def request(command, expected):
        calls.append(command)
        if command.startswith('SET'):
            raise ProtocolError('SESSION')
        return 'EXPIRED'

    controller._request = request
    with pytest.raises(ProtocolError):
        controller.set_state(buttons=4)
    assert calls[-1] == 'STATUS'
    assert controller.failure is not None
    assert controller.stopped.is_set()


def test_heartbeat_does_not_recover_pressed_state(monkeypatch):
    from automation.adapters.serial_controller import ProtocolError
    controller = SerialController('COM8')
    controller.state = (4, 8, 128, 128, 128, 128)
    calls = []

    def request(command, expected):
        calls.append(command)
        if command == 'KEEP':
            raise ProtocolError('SESSION')
        return 'EXPIRED'

    controller._request = request
    monkeypatch.setattr(controller.stopped, 'wait', lambda _: False)
    controller._heartbeat()
    assert calls == ['KEEP', 'STATUS']
    assert controller.failure is not None
    assert controller.stopped.is_set()


def test_heartbeat_does_not_recover_during_timed_operation(monkeypatch):
    controller = SerialController('COM8')
    controller.timed_inflight = True
    calls = []

    def request(command, expected):
        calls.append(command)
        raise TimeoutError('lost')

    controller._request = request
    monkeypatch.setattr(controller.stopped, 'wait', lambda _: False)
    controller._heartbeat()
    assert calls == ['KEEP']
    assert controller.failure is not None
    assert controller.stopped.is_set()
