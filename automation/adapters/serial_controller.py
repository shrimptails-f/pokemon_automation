import logging
import secrets
import threading
import time

from .controller_protocol import decode_frame, encode_frame

logger = logging.getLogger(__name__)

BUTTONS = {name: bit for bit, name in enumerate(("Y", "B", "A", "X", "L", "R", "ZL", "ZR", "MINUS", "PLUS", "LSTICK", "RSTICK", "HOME", "CAPTURE"))}
HATS = {"UP": 0, "RIGHT": 2, "DOWN": 4, "LEFT": 6}
NEUTRAL = (0, 8, 128, 128, 128, 128)
RESPONSE_TIMEOUT = 0.35
ATTEMPTS = 3
HEARTBEAT_INTERVAL = 0.4
LEASE_SECONDS = 2.0
RECOVERY_ATTEMPTS = 6
RECOVERY_INTERVAL = 0.5
assert LEASE_SECONDS > HEARTBEAT_INTERVAL + RESPONSE_TIMEOUT * ATTEMPTS
assert RECOVERY_INTERVAL * (RECOVERY_ATTEMPTS - 1) > LEASE_SECONDS


class ProtocolError(RuntimeError):
    def __init__(self, result):
        self.result = result
        super().__init__(f"Arduino 応答エラー: {result}")


class SerialController:
    def __init__(self, port_name):
        self.port_name = port_name
        self.port = None
        self.session = secrets.randbits(32) or 1
        self.sequence = 0
        self.lock = threading.RLock()
        self.operation_lock = threading.Lock()
        self.stopped = threading.Event()
        self.failure = None
        self.state = NEUTRAL
        self.timed_inflight = False

    def __enter__(self):
        import serial
        self.port = serial.Serial(self.port_name, 115200, timeout=0.15, write_timeout=0.5)
        try:
            self.port.write(b"\n")
            time.sleep(0.5)
            self.port.reset_input_buffer()
            self._establish_session()
            self.thread = threading.Thread(target=self._heartbeat, daemon=True)
            self.thread.start()
        except BaseException:
            self.port.close()
            raise
        return self

    def _request(self, command, expected):
        with self.lock:
            if self.failure:
                raise RuntimeError("コントローラー通信が停止しました") from self.failure
            seq = self.sequence
            frame = encode_frame(f"2,{self.session},{seq},{command}")
            for _ in range(ATTEMPTS):
                deadline = time.monotonic() + RESPONSE_TIMEOUT
                self.port.write_timeout = RESPONSE_TIMEOUT
                self.port.write(frame)
                while time.monotonic() < deadline:
                    self.port.timeout = min(0.15, max(0, deadline - time.monotonic()))
                    raw = self.port.readline()
                    try:
                        fields = decode_frame(raw).split(",")
                    except ValueError:
                        continue
                    if len(fields) != 5 or fields[:4] != ["2", str(self.session), str(seq), command.split(",", 1)[0]]:
                        continue
                    if expected is not None and fields[4] != expected:
                        raise ProtocolError(fields[4])
                    return fields[4]
            raise TimeoutError("Arduino 応答がありません。操作結果は不明です")

    def _establish_session(self):
        for attempt in range(RECOVERY_ATTEMPTS):
            try:
                self._request("HELLO", "ACTIVE")
                return
            except ProtocolError as exc:
                if exc.result != "SESSION":
                    raise
                status = self._request("STATUS", None)
                if status not in ("READY", "ACTIVE", "EXPIRED"):
                    raise ProtocolError(status)
                if status != "ACTIVE":
                    self.session = secrets.randbits(32) or 1
                if attempt == RECOVERY_ATTEMPTS - 1:
                    raise
                time.sleep(RECOVERY_INTERVAL)

    def _recover_neutral(self):
        # Called under lock only when no SET is in flight and the last confirmed
        # state is neutral. Never re-send a state whose result is unknown.
        last_error = None
        for attempt in range(RECOVERY_ATTEMPTS):
            try:
                status = self._request("STATUS", None)
                if status == "ACTIVE":
                    try:
                        self._request("KEEP", "ACTIVE")
                        return
                    except ProtocolError as exc:
                        if exc.result != "SESSION":
                            raise
                elif status in ("READY", "EXPIRED"):
                    old_session = self.session
                    while self.session == old_session:
                        self.session = secrets.randbits(32) or 1
                    self.sequence = 0
                    self._request("HELLO", "ACTIVE")
                    return
                else:
                    raise ProtocolError(status)
            except (OSError, TimeoutError, ProtocolError) as exc:
                last_error = exc
                if isinstance(exc, OSError) and not isinstance(exc, TimeoutError):
                    try:
                        import serial
                        self.port.close()
                        self.port = serial.Serial(self.port_name, 115200, timeout=0.15, write_timeout=0.5)
                        self.port.write(b"\n")
                        self.port.reset_input_buffer()
                    except OSError as reopen_error:
                        last_error = reopen_error
            if attempt + 1 < RECOVERY_ATTEMPTS:
                if self.stopped.wait(RECOVERY_INTERVAL):
                    raise RuntimeError("復旧を中止しました")
        raise RuntimeError("中立状態からの通信復旧に失敗しました") from last_error

    def _heartbeat(self):
        while not self.stopped.wait(HEARTBEAT_INTERVAL):
            with self.lock:
                try:
                    self._request("KEEP", "ACTIVE")
                except Exception as exc:
                    if self.state == NEUTRAL and not self.failure and not self.timed_inflight:
                        try:
                            self._recover_neutral()
                            continue
                        except Exception as recovery_error:
                            exc = recovery_error
                    if isinstance(exc, ProtocolError) and exc.result == "SESSION":
                        try:
                            logger.warning("更新拒否後の Arduino 状態: %s", self._request("STATUS", None))
                        except Exception:
                            logger.warning("Arduino の状態を確認できませんでした", exc_info=True)
                    self.failure = exc
                    self.stopped.set()
                    return

    def set_state(self, buttons=0, hat=8, x=128, y=128, rx=128, ry=128):
        with self.operation_lock:
            self._set_state(buttons, hat, x, y, rx, ry)

    def _set_state(self, buttons=0, hat=8, x=128, y=128, rx=128, ry=128):
        values = (buttons, hat, x, y, rx, ry)
        if any(not isinstance(v, int) or not 0 <= v <= limit for v, limit in zip(values, (65535, 8, 255, 255, 255, 255))):
            raise ValueError("入力状態が範囲外です")
        with self.lock:
            if self.sequence == 0xffffffff:
                raise RuntimeError("要求番号を使い切りました")
            self.sequence += 1
            try:
                self._request("SET," + ",".join(map(str, values)), "APPLIED")
                self.state = values
            except Exception as exc:
                if isinstance(exc, ProtocolError) and exc.result == "SESSION":
                    try:
                        logger.warning("状態指定拒否後の Arduino 状態: %s", self._request("STATUS", None))
                    except Exception:
                        logger.warning("Arduino の状態を確認できませんでした", exc_info=True)
                self.failure = exc
                self.stopped.set()
                raise

    def send(self, command):
        with self.operation_lock:
            self._send(command)

    def _send(self, command):
        with self.lock:
            state = list(self.state)
            if command in BUTTONS:
                state[0] |= 1 << BUTTONS[command]
                duration_ms = 150
            elif command in HATS:
                state[1] = HATS[command]
                duration_ms = 150
            elif command.startswith("STICK_UP "):
                try:
                    duration_ms = int(command[9:])
                except ValueError as exc:
                    raise ValueError("移動時間が不正です") from exc
                if not 1 <= duration_ms <= 3000:
                    raise ValueError("移動時間が範囲外です")
                state[3] = 0
            else:
                raise ValueError(f"不明な操作: {command}")
            if self.sequence == 0xffffffff:
                raise RuntimeError("要求番号を使い切りました")
            self.sequence += 1
            self.timed_inflight = True
            command = "TIMED," + ",".join(map(str, (*state, *self.state, duration_ms)))

        deadline = time.monotonic() + duration_ms / 1000 + RESPONSE_TIMEOUT * ATTEMPTS + 2
        try:
            while True:
                result = self._request(command, None)
                if result == "DONE":
                    return
                if result != "RUNNING":
                    raise ProtocolError(result)
                if time.monotonic() >= deadline:
                    raise TimeoutError("Arduino の操作完了を確認できません")
                if self.stopped.wait(min(0.05, max(0, deadline - time.monotonic()))):
                    raise RuntimeError("コントローラー通信が停止しました") from self.failure
        except Exception as exc:
            with self.lock:
                self.failure = exc
                self.stopped.set()
            raise
        finally:
            with self.lock:
                self.timed_inflight = False

    def __exit__(self, *args):
        self.stopped.set()
        self.thread.join()
        try:
            if not self.failure:
                self.set_state(*NEUTRAL)
        finally:
            self.port.close()
