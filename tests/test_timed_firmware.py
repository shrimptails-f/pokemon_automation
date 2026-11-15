import shutil
import subprocess
from pathlib import Path

import pytest


def test_firmware_timed_operation(tmp_path):
    compiler = shutil.which('g++')
    if not compiler:
        pytest.skip('g++ がありません')
    root = Path(__file__).resolve().parents[1]
    # Compile the real sketch with hardware stubs; do not maintain a copy of it.
    harness = (root / 'tests/firmware/timed_input.cpp').read_text()
    sketch = (root / 'controller/switch_arduino_micro/switch_arduino_micro.ino').read_text()
    harness = harness.replace('// SKETCH', sketch.split('\n', 1)[1])
    source = tmp_path / 'test.cpp'
    source.write_text(harness)
    binary = tmp_path / 'test'
    subprocess.run([compiler, '-std=c++11', str(source), '-o', str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
