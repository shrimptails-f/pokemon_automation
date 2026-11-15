import logging
import secrets
import threading
import time

from .controller_protocol import decode_frame, encode_frame

logger = logging.getLogger(__name__)

BUTTONS = {name: bit for bit, name in enumerate(("Y", "B", "A", "X", "L", "R", "ZL", "ZR", "MINUS", "PLUS", "LSTICK", "RSTICK", "HOME", "CAPTURE"))}
HATS = {"UP": 0, "RIGHT": 2, "DOWN": 4, "LEFT": 6}
NEUTRAL = (0, 8, 128, 128, 128, 128)


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

    def __enter__(self):
        import serial
        self.port = serial.Serial(self.port_name, 115200, timeout=0.15, write_timeout=0.5)
        try:
            self.port.write(b"\n")
            time.sleep(0.5)
            self.port.reset_input_buffer()
            for attempt in range(6):
                try:
                    self._request("HELLO", expected="ACTIVE")
                    break
                except RuntimeError as exc:
                    if "SESSION" not in str(exc) or attempt == 5:
                        raise
                    time.sleep(0.5)
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
            frame = encode_frame(f"1,{self.session},{seq},{command}")
            for _ in range(3):
                self.port.write(frame)
                deadline = time.monotonic() + 0.35
                while time.monotonic() < deadline:
                    raw = self.port.readline()
                    try:
                        fields = decode_frame(raw).split(",")
                    except ValueError:
                        continue
                    if len(fields) != 5 or fields[:4] != ["1", str(self.session), str(seq), command.split(",", 1)[0]]:
                        continue
                    if fields[4] != expected:
                        raise RuntimeError(f"Arduino 応答エラー: {fields[4]}")
                    return
            raise TimeoutError("Arduino 応答がありません。操作結果は不明です")

    def _heartbeat(self):
        while not self.stopped.wait(0.4):
            try:
                self._request("KEEP", "ACTIVE")
            except Exception as exc:
                self.failure = exc
                self.stopped.set()
                return

    def set_state(self, buttons=0, hat=8, x=128, y=128, rx=128, ry=128):
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
                self.failure = exc
                raise

    def send(self, command):
        with self.operation_lock:
            self._send(command)

    def _send(self, command):
        with self.lock:
            state = list(self.state)
            if command in BUTTONS:
                state[0] |= 1 << BUTTONS[command]
                duration = 0.15
            elif command in HATS:
                state[1] = HATS[command]
                duration = 0.15
            elif command.startswith("STICK_UP "):
                try:
                    ms = int(command[9:])
                except ValueError as exc:
                    raise ValueError("移動時間が不正です") from exc
                if not 1 <= ms <= 3000:
                    raise ValueError("移動時間が範囲外です")
                state[3] = 0
                duration = ms / 1000
            else:
                raise ValueError(f"不明な操作: {command}")
            previous = self.state
            self.set_state(*state)
        # Heartbeat continues while waiting. Do not release after a communication failure.
        if self.stopped.wait(duration):
            raise RuntimeError("コントローラー通信が停止しました") from self.failure
        self.set_state(*previous)

    def __exit__(self, *args):
        self.stopped.set()
        self.thread.join()
        try:
            if not self.failure:
                self.set_state(*NEUTRAL)
        finally:
            self.port.close()
