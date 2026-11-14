import logging

import pytest
import serial

from automation.adapters import serial_controller


@pytest.mark.parametrize('response', [b'', b'ERR\r\n'])
def test_handshake_failure_logs_response_and_closes_port(monkeypatch, caplog, response):
    class FakePort:
        closed = False

        def write(self, data):
            pass

        def reset_input_buffer(self):
            pass

        def readline(self):
            return response

        def close(self):
            self.closed = True

    port = FakePort()
    monkeypatch.setattr(serial, 'Serial', lambda *args, **kwargs: port)
    monkeypatch.setattr(serial_controller.time, 'sleep', lambda _: None)
    with caplog.at_level(logging.DEBUG, logger=serial_controller.__name__):
        with pytest.raises(RuntimeError, match='接続確認に失敗'):
            with serial_controller.SerialController('COM8'):
                pass
    assert f'raw={response!r}' in caplog.text
    assert port.closed


def test_delayed_initial_error_is_followed_by_pong(monkeypatch, caplog):
    class FakePort:
        timeout = 5
        responses = iter([b'ERR\r\n', b'PONG\r\n'])
        closed = False

        def write(self, data):
            pass

        def reset_input_buffer(self):
            pass

        def readline(self):
            return next(self.responses)

        def close(self):
            self.closed = True

    port = FakePort()
    monkeypatch.setattr(serial, 'Serial', lambda *args, **kwargs: port)
    monkeypatch.setattr(serial_controller.time, 'sleep', lambda _: None)
    with caplog.at_level(logging.DEBUG, logger=serial_controller.__name__):
        with serial_controller.SerialController('COM8') as controller:
            assert controller.port is port
            assert port.timeout == 5
    assert "raw=b'ERR\\r\\n'" in caplog.text
    assert "raw=b'PONG\\r\\n'" in caplog.text
    assert port.closed
