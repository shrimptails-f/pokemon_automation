import logging
import time

logger = logging.getLogger(__name__)


class SerialController:
    def __init__(self, port_name):
        self.port_name = port_name
        self.port = None

    def __enter__(self):
        import serial
        logger.debug("シリアルポートを開きます: port=%s baudrate=115200 timeout=5 write_timeout=2", self.port_name)
        try:
            self.port = serial.Serial(self.port_name, 115200, timeout=5, write_timeout=2)
        except Exception:
            logger.debug("シリアルポートを開けませんでした", exc_info=True)
            raise
        logger.debug("シリアルポートを開きました")
        try:
            logger.debug("初期化: 改行を送信し、0.5 秒待機します")
            self.port.write(b"\n")
            time.sleep(0.5)
            logger.debug("初期化: 受信バッファを消去し、PING を送信します")
            self.port.reset_input_buffer()
            self.port.write(b"PING\n")
            start = time.monotonic()
            response = self.port.readline()
            responses = [response]
            logger.debug("PING 応答: raw=%r elapsed=%.3f 秒（空の場合は受信タイムアウト）",
                         response, time.monotonic() - start)
            if response.strip() == b"ERR":
                # The initial newline may have produced an ERR after the input buffer was cleared.
                # Accept the connection only if the following response is PONG.
                remaining = max(0, 5 - (time.monotonic() - start))
                if remaining:
                    self.port.timeout = remaining
                    try:
                        response = self.port.readline()
                        responses.append(response)
                    finally:
                        self.port.timeout = 5
                    logger.debug("PING 応答（次の行）: raw=%r elapsed=%.3f 秒", response, time.monotonic() - start)
            if response.strip() != b"PONG":
                raise RuntimeError(f"Arduino の接続確認に失敗しました: port={self.port_name} PING 応答={responses!r}")
        except BaseException:
            logger.debug("接続確認に失敗したためポートを閉じます", exc_info=True)
            self.port.close()
            raise
        return self

    def send(self, command):
        logger.debug("コマンド送信: %s", command)
        self.port.write((command + "\n").encode("ascii"))
        start = time.monotonic()
        response = self.port.readline().strip()
        logger.debug("コマンド応答: command=%s response=%r elapsed=%.3f 秒", command, response, time.monotonic() - start)
        if response != b"OK":
            raise RuntimeError(f"{command} の応答エラー: {response!r}")

    def __exit__(self, *args):
        logger.debug("シリアルポートを閉じます: %s", self.port_name)
        self.port.close()
