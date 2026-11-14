import time


class SerialController:
    def __init__(self, port_name):
        self.port_name = port_name
        self.port = None

    def __enter__(self):
        import serial
        self.port = serial.Serial(self.port_name, 115200, timeout=5, write_timeout=2)
        try:
            self.port.write(b"\n")
            time.sleep(0.5)
            self.port.reset_input_buffer()
            self.port.write(b"PING\n")
            if self.port.readline().strip() != b"PONG":
                raise RuntimeError("Arduino の接続確認に失敗しました。")
        except BaseException:
            self.port.close()
            raise
        return self

    def send(self, command):
        self.port.write((command + "\n").encode("ascii"))
        response = self.port.readline().strip()
        if response != b"OK":
            raise RuntimeError(f"{command} の応答エラー: {response!r}")

    def __exit__(self, *args):
        self.port.close()
