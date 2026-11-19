"""Save capture frames at a fixed rate to a per-encounter MP4."""
import shutil
import tempfile
from pathlib import Path

import cv2


class EncounterVideo:
    def __init__(self, path, fps=10):
        self.path = Path(path)
        self.fps = fps
        self.temporary = tempfile.TemporaryDirectory()
        # OpenCV on Windows may fail to open non-ASCII paths.
        self.temp_path = Path(self.temporary.name) / 'encounter.mp4'
        self.writer = None
        self.first_time = None
        self.last_frame = None
        self.count = 0

    def add(self, frame, timestamp):
        if self.writer is None:
            height, width = frame.shape[:2]
            self.writer = cv2.VideoWriter(str(self.temp_path), cv2.VideoWriter_fourcc(*'mp4v'),
                                          self.fps, (width, height))
            if not self.writer.isOpened():
                raise RuntimeError('動画を作成できません。')
            self.first_time = timestamp
        target = int(max(0, timestamp - self.first_time) * self.fps)
        if target - self.count > self.fps * 5:
            raise RuntimeError('動画の撮影が5秒以上中断しました。')
        while self.count < target:
            self.writer.write(self.last_frame if self.last_frame is not None else frame)
            self.count += 1
        if self.count == target:
            self.writer.write(frame)
            self.count += 1
            self.last_frame = frame.copy()

    def close(self):
        try:
            if self.writer is not None:
                self.writer.release()
            if not self.count or not self.temp_path.exists() or self.temp_path.stat().st_size == 0:
                raise RuntimeError('動画を保存できませんでした。')
            shutil.copyfile(self.temp_path, self.path)
        finally:
            self.temporary.cleanup()
