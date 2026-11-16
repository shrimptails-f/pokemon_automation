"""Persistent serial evidence and generation-checked rejected-frame retrieval."""
from collections import deque
from datetime import datetime, timezone
from difflib import SequenceMatcher
import json
import re
import time

from tools.controller_diagnostics import exchange


class LoggedPort:
    def __init__(self, port, log):
        self.port = port
        self.log = log
        self.sent = deque(maxlen=256)

    def event(self, kind, **fields):
        record = dict(time=datetime.now(timezone.utc).isoformat(), monotonic=time.monotonic(), kind=kind, **fields)
        self.log.write(json.dumps(record, ensure_ascii=False) + '\n')
        self.log.flush()
        return record

    def write(self, data):
        entry = self.event('tx', hex=data.hex(), length=len(data))
        for frame in data.split(b'\n'):
            if frame:
                self.sent.append((entry['time'], frame))
        try:
            size = self.port.write(data)
        except OSError as exc:
            self.event('write_error', error=str(exc))
            raise
        self.event('write_result', written=size)
        if size != len(data):
            raise OSError(f'部分書き込み: {size}/{len(data)} バイト')
        return size

    def readline(self):
        try:
            raw = self.port.readline()
        except OSError as exc:
            self.event('read_error', error=str(exc))
            raise
        self.event('rx', hex=raw.hex(), length=len(raw))
        return raw


def read_capture(port, *, timeout=0.5, attempts=3, restarts=3):
    """Return (id, bytes), or None. Never combine different generations."""
    for restart in range(restarts):
        record_id = 0
        total = None
        data = bytearray()
        while True:
            result = exchange(port, f'DUMP,{record_id},{len(data)}', timeout=timeout, attempts=attempts)
            if result == 'NONE':
                if record_id:
                    raise ValueError('読み出し中に記録が消失しました（再起動の可能性）')
                return None
            if result == 'STALE':
                if hasattr(port, 'event'):
                    port.event('capture_changed', restart=restart + 1, record_id=record_id)
                break
            fields = result.split(':')
            if len(fields) != 4 or any(not re.fullmatch(r'[0-9]+', x) for x in fields[:3]):
                raise ValueError(f'保存記録の応答が不正です: {result}')
            generation, size, offset = map(int, fields[:3])
            if not 1 <= generation <= 0xffffffff or not 1 <= size <= 159 or offset != len(data):
                raise ValueError('保存記録の番号・長さ・位置が不正です')
            if record_id and (generation != record_id or size != total):
                raise ValueError('保存記録の番号または長さが途中で変わりました')
            if not re.fullmatch(r'(?:[0-9A-F]{2}){1,32}', fields[3]):
                raise ValueError('保存記録の16進データが不正です')
            chunk = bytes.fromhex(fields[3])
            if len(chunk) != min(32, size - offset):
                raise ValueError('保存記録の分割長が不正です')
            record_id, total = generation, size
            data.extend(chunk)
            if len(data) == total:
                return record_id, bytes(data)
    raise RuntimeError('保存記録の更新が続いたため取得できませんでした')


def compare_history(raw, history, limit=3):
    """Rank candidate transmissions, not proof of which request was received."""
    unique = {}
    for timestamp, frame in history:
        unique[frame] = timestamp
    candidates = []
    for frame, timestamp in unique.items():
        matcher = SequenceMatcher(None, frame, raw, autojunk=False)
        changes = []
        for tag, a, b, c, d in matcher.get_opcodes():
            if tag != 'equal':
                changes.append(dict(kind={'replace': '変化', 'delete': '欠落', 'insert': '混入'}[tag],
                                    sent_offset=a, received_offset=c,
                                    sent_hex=frame[a:b].hex(), received_hex=raw[c:d].hex()))
        candidates.append(dict(time=timestamp, sent_hex=frame.hex(), score=matcher.ratio(), changes=changes))
    return sorted(candidates, key=lambda x: (x['score'], x['time']), reverse=True)[:limit]


def report_capture(port, **kwargs):
    try:
        result = read_capture(port, **kwargs)
        if result is None:
            port.event('capture_none')
            print('CRC 不一致の保存記録はありません。', flush=True)
            return
        record_id, raw = result
        candidates = compare_history(raw, port.sent)
        port.event('capture', record_id=record_id, length=len(raw), hex=raw.hex(), candidates=candidates)
        print(f'保存記録 #{record_id}: 長さ={len(raw)} HEX={raw.hex()}', flush=True)
        print('送信候補との比較（対応や原因の確定ではありません。位置は0始まり）:', flush=True)
        for candidate in candidates:
            print(f"  TX {candidate['time']} HEX={candidate['sent_hex']}", flush=True)
            for change in candidate['changes']:
                print(f"    {change['kind']}: TX[{change['sent_offset']}]={change['sent_hex']} "
                      f"RX[{change['received_offset']}]={change['received_hex']}", flush=True)
        if not candidates:
            print('  この実行の送信履歴に候補がありません。', flush=True)
    except (OSError, ValueError, RuntimeError) as exc:
        port.event('capture_error', error=str(exc))
        print(f'保存記録を取得できませんでした: {exc}（試行結果はログを参照）', flush=True)
