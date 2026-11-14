import sys


class OpenCVCapture:
    def __init__(self, device):
        import cv2
        self.cv2 = cv2
        self.capture = cv2.VideoCapture(device, cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY)

    def __enter__(self):
        if not self.capture.isOpened():
            self.capture.release()
            raise RuntimeError("キャプチャー機器を開けません。")
        return self

    def read(self):
        ok, frame = self.capture.read()
        if not ok or frame is None:
            raise RuntimeError("映像を取得できません。")
        return frame

    def save(self, frame, path):
        success, encoded = self.cv2.imencode(".png", frame)
        if not success:
            raise RuntimeError("画像をエンコードできませんでした。")
        path.write_bytes(encoded.tobytes())

    def __exit__(self, *args):
        self.capture.release()
