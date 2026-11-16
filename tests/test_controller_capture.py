import io
import json

import pytest

from automation.adapters.controller_protocol import decode_frame, encode_frame
from tools.controller_capture import LoggedPort, compare_history, read_capture, report_capture
from tools.controller_diagnostics import exchange
from tools.controller_single_request_test import run


class Port:
    def __init__(self, handler):
        self.handler = handler
        self.pending = []
        self.requests = []

    def write(self, frame):
        if frame.strip():
            fields = decode_frame(frame.lstrip(b'\n')).split(',')
            self.requests.append(fields)
            result = self.handler(fields)
            if result is not None:
                self.pending.append(encode_frame(','.join(fields[:4] + [result])))
        return len(frame)

    def readline(self):
        return self.pending.pop(0) if self.pending else b''


def test_capture_restarts_after_generation_changes_and_preserves_binary():
    raw = b'2,' + bytes(range(1, 60))
    changed = False

    def respond(fields):
        nonlocal changed
        generation, offset = map(int, fields[4:])
        if generation == 1 and offset == 32:
            changed = True
            return 'STALE'
        generation = 2 if changed else 1
        return f'{generation}:{len(raw)}:{offset}:{raw[offset:offset+32].hex().upper()}'

    backend = Port(respond)
    log = io.StringIO()
    port = LoggedPort(backend, log)
    assert read_capture(port) == (2, raw)
    events = [json.loads(line) for line in log.getvalue().splitlines()]
    assert any(e['kind'] == 'capture_changed' for e in events)
    assert len([e for e in events if e['kind'] == 'tx']) == len(backend.requests)
    assert all('time' in e and 'monotonic' in e for e in events)


@pytest.mark.parametrize('reply', ['1:4:0:ABC', '1:4:1:00010203', '1:4:0:00', '0:4:0:00010203'])
def test_capture_rejects_malformed_chunks(reply):
    with pytest.raises(ValueError):
        read_capture(Port(lambda _: reply))


def test_capture_repeated_updates_fail_explicitly():
    with pytest.raises(RuntimeError, match='更新'):
        read_capture(Port(lambda _: 'STALE'), restarts=2)


def test_exchange_reassembles_partial_response_and_logs_retry():
    backend = Port(lambda _: None)
    original_write = backend.write
    def write(frame):
        count = original_write(frame)
        if len(backend.requests) == 2:
            fields = backend.requests[-1]
            response = encode_frame(','.join(fields[:4] + ['READY']))
            backend.pending = [response[:5], response[5:]]
        return count
    backend.write = write
    log = io.StringIO()
    port = LoggedPort(backend, log)
    assert exchange(port, 'STATUS', timeout=.001, attempts=2) == 'READY'
    events = [json.loads(line) for line in log.getvalue().splitlines()]
    assert len([e for e in events if e['kind'] == 'tx']) == 2
    assert any(e['kind'] == 'timeout' and e['attempt'] == 1 for e in events)
    assert len([e for e in events if e['kind'] == 'rx' and e['length']]) == 2


@pytest.mark.parametrize(('received', 'kind'), [(b'abXdef', '変化'), (b'abdef', '欠落'), (b'abQcdef', '混入')])
def test_comparison_classifies_offsets(received, kind):
    candidate = compare_history(received, [('now', b'abcdef')])[0]
    assert candidate['changes'][0]['kind'] == kind
    assert candidate['changes'][0]['sent_offset'] == 2
    assert candidate['changes'][0]['received_offset'] == 2


def test_failed_diag_still_captures_and_keeps_status_result(capsys):
    diag_count = 0
    def respond(fields):
        nonlocal diag_count
        if fields[3] == 'DIAG':
            diag_count += 1
            return '1:0:0:0:0:0:0:0:0:0:NONE' if diag_count == 1 else None
        if fields[3] == 'STATUS':
            return 'READY'
        return '1:3:0:322C00'
    log = io.StringIO()
    port = LoggedPort(Port(respond), log)
    assert run(port, 1, .001) is False
    events = [json.loads(line) for line in log.getvalue().splitlines()]
    assert any(e['kind'] == 'status_result' and 'READY' in e['result'] for e in events)
    assert any(e['kind'] == 'capture' and e['hex'] == '322c00' for e in events)
    assert '診断を中断' in capsys.readouterr().out


def test_capture_timeout_is_recorded(capsys):
    log = io.StringIO()
    port = LoggedPort(Port(lambda _: None), log)
    report_capture(port, timeout=.001, attempts=2)
    events = [json.loads(line) for line in log.getvalue().splitlines()]
    assert any(e['kind'] == 'capture_error' for e in events)
    assert len([e for e in events if e['kind'] == 'tx']) == 2
    assert '取得できません' in capsys.readouterr().out
