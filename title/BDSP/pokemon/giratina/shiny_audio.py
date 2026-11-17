"""色違い効果音の参照区間と録音を照合する実験用ツール。"""
import argparse
import io
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import numpy as np

RATE = 16000


class AudioRecorder:
    """Record throughout an encounter; reject incomplete input."""
    def __init__(self, device=None):
        self.device = device
        self.chunks = []
        self.errors = []
        self.stream = None
        self.started_at = None
        self.video_started_at = None
        self.stopped = False

    def __enter__(self):
        import sounddevice as sd

        def callback(indata, frames, time_info, status):
            if status:
                self.errors.append(str(status))
            self.chunks.append(indata[:, 0].copy())

        self.stream = sd.InputStream(device=self.device, samplerate=RATE, channels=1,
                                     dtype='float32', callback=callback)
        self.started_at = time.monotonic()
        self.stream.start()
        return self

    def mark_video_start(self):
        self.video_started_at = time.monotonic()

    def __exit__(self, *args):
        try:
            self.stop()
        finally:
            self.stream.close()

    def stop(self):
        if not self.stopped:
            self.stream.stop()
            self.stopped = True

    def samples(self):
        if self.errors or not self.chunks:
            raise RuntimeError(f'音声入力が不完全です: {", ".join(self.errors) or "録音なし"}')
        samples = np.concatenate(self.chunks).astype(np.float64)
        if np.max(np.abs(samples)) < 1e-5:
            raise RuntimeError('音声入力が無音です。入力デバイスを確認してください。')
        return samples


def add_audio_to_video(path, samples, offset):
    """Mux captured audio from the start of the video; replace only on success."""
    from imageio_ffmpeg import get_ffmpeg_exe

    start = max(0, round(offset * RATE))
    audio = samples[start:]
    if len(audio) < RATE // 10:
        raise RuntimeError('動画に対応する音声が不足しています。')
    pcm = (np.clip(audio, -1, 1) * 32767).astype('<i2')
    buffer = io.BytesIO()
    with wave.open(buffer, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(RATE)
        wav.writeframes(pcm.tobytes())
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / 'video.mp4'
        result = Path(temp) / 'video-audio.mp4'
        shutil.copyfile(path, source)
        command = [get_ffmpeg_exe(), '-v', 'error', '-i', str(source), '-i', 'pipe:0',
                   '-map', '0:v:0', '-map', '1:a:0', '-c:v', 'copy', '-c:a', 'aac',
                   '-shortest', '-y', str(result)]
        process = subprocess.run(command, input=buffer.getvalue(), capture_output=True, check=False)
        if process.returncode or not result.exists() or not result.stat().st_size:
            raise RuntimeError(f'動画に音声を保存できません: {process.stderr.decode(errors="replace")}')
        shutil.copyfile(result, path)


def read_audio(path, start=None, duration=None):
    from imageio_ffmpeg import get_ffmpeg_exe

    command = [get_ffmpeg_exe(), '-v', 'error']
    if start is not None:
        command += ['-ss', str(start)]
    command += ['-i', str(path)]
    if duration is not None:
        command += ['-t', str(duration)]
    command += ['-vn', '-ac', '1', '-ar', str(RATE), '-f', 'f32le', 'pipe:1']
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f'音声を読み込めません: {result.stderr.decode(errors="replace")}')
    samples = np.frombuffer(result.stdout, dtype='<f4').astype(np.float64)
    if not len(samples):
        raise ValueError(f'音声がありません: {path}')
    return samples


def correlate(recording, template):
    """各位置の平均と音量を正規化した相互相関の最大値を返す。"""
    n = len(template)
    if n < 2 or len(recording) < n:
        raise ValueError('照合音声は参照区間以上の長さが必要です。')
    template = template - template.mean()
    norm = np.linalg.norm(template)
    if norm < 1e-10:
        raise ValueError('参照区間が無音です。')
    size = 1 << (len(recording) + n - 2).bit_length()
    convolution = np.fft.irfft(np.fft.rfft(recording, size) * np.fft.rfft(template[::-1], size), size)
    dot = convolution[n - 1:len(recording)]
    sums = np.concatenate(([0.0], np.cumsum(recording)))
    squares = np.concatenate(([0.0], np.cumsum(recording * recording)))
    energy = np.maximum(0, squares[n:] - squares[:-n] - (sums[n:] - sums[:-n]) ** 2 / n)
    denominator = np.sqrt(energy) * norm
    scores = np.divide(dot, denominator, out=np.zeros_like(dot), where=denominator > 1e-10)
    index = int(np.argmax(scores))
    return float(np.clip(scores[index], -1, 1)), index / RATE


def main():
    parser = argparse.ArgumentParser(description='色違い効果音の音声相関を確認する実験ツール')
    parser.add_argument('--reference', type=Path, required=True, help='参照動画または音声')
    parser.add_argument('--start', type=float, required=True, help='参照開始秒')
    parser.add_argument('--end', type=float, required=True, help='参照終了秒')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', type=Path, help='照合する動画または音声')
    source.add_argument('--record', type=float, help='音声入力から録音する秒数')
    parser.add_argument('--device', type=int, help='録音する音声入力デバイス番号')
    parser.add_argument('--threshold', type=float, default=0.7, help='候補とする相関値（仮値）')
    args = parser.parse_args()
    if args.start < 0 or args.end <= args.start or not 0 < args.threshold <= 1 or (args.record is not None and args.record <= 0):
        parser.error('参照時間、録音時間、しきい値を確認してください。')
    try:
        template = read_audio(args.reference, args.start, args.end - args.start)
        if args.input:
            recording = read_audio(args.input)
        else:
            import sounddevice as sd
            print('録音を開始します。', flush=True)
            recording = sd.rec(round(args.record * RATE), samplerate=RATE, channels=1,
                               dtype='float32', device=args.device, blocking=True)[:, 0].astype(np.float64)
        score, at = correlate(recording, template)
        print(f'最大相関: {score:.4f} / 開始位置: {at:.3f} 秒 / しきい値: {args.threshold:.3f}')
        print('色違い音候補（要確認）' if score >= args.threshold else '候補なし（見逃しの可能性あり）')
    except (ValueError, OSError, ImportError) as exc:
        sys.exit(f'音声照合を停止しました: {exc}')


if __name__ == '__main__':
    main()
