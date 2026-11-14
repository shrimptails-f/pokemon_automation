import sys

import pytest

from title.BDSP import main as app


def test_connection_is_reused_and_closed_after_discord_loop(monkeypatch):
    events = []

    class Controller:
        def __init__(self, port):
            events.append(('open', port))

        def __enter__(self):
            return self

        def __exit__(self, *args):
            events.append(('close',))

        def send(self, command):
            events.append(('send', command))

    class Capture:
        def __init__(self, device):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def read(self):
            pass

    def discord_main(args, encounter, reset, run_loop, stop, legacy_env):
        events.append(('thread',))
        reset()
        encounter()
        reset()

    monkeypatch.setattr(sys, 'argv', ['review_loop.py', 'COM8', '--move-ms', '500', '--a-after', '15', '--discord'])
    monkeypatch.setattr(app, 'SerialController', Controller)
    monkeypatch.setattr(app, 'OpenCVCapture', Capture)
    monkeypatch.setattr(app, 'reset', lambda controller, **kwargs: controller.send('HOME'))
    import automation.adapters.discord.review as discord_review
    monkeypatch.setattr(discord_review, 'main', discord_main)
    monkeypatch.setattr(app, 'encounter', lambda controller, *args, **kwargs: controller.send('A'))
    app.main()
    assert events == [('open', 'COM8'), ('thread',), ('send', 'HOME'), ('send', 'A'),
                      ('send', 'HOME'), ('close',)]


def test_connection_failure_prevents_discord_start(monkeypatch, capsys):
    class Controller:
        def __init__(self, port):
            pass

        def __enter__(self):
            raise RuntimeError("PING 応答=[b'ERR\\r\\n']")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(sys, 'argv', ['review_loop.py', 'COM8', '--move-ms', '500', '--a-after', '15', '--discord'])
    monkeypatch.setattr(app, 'SerialController', Controller)
    with pytest.raises(SystemExit, match='PING 応答'):
        app.main()
    assert 'スレッド:' not in capsys.readouterr().out
