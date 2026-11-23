"""Experimental detection of transient bright effects in encounter frames."""
import re
from pathlib import Path

import cv2
import numpy as np

from title.BDSP.pokemon.giratina.classify import TEMPLATES

FRAME = re.compile(r'frame_\d+_([\d.]+)s\.png$')


def detect_sparkle(directory):
    """Return True/False, or None when the post-dialogue window is incomplete."""
    frames = []
    template = cv2.imread(str(TEMPLATES / 'dialog_encounter.png'), cv2.IMREAD_GRAYSCALE)
    if template is None:
        return None, []
    sendout_template = cv2.imread(str(TEMPLATES / 'dialog_sendout.png'), cv2.IMREAD_GRAYSCALE)
    for path in sorted(Path(directory).glob('frame_*.png')):
        match = FRAME.fullmatch(path.name)
        if not match:
            continue
        image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f'画像を読み込めません: {path}')
        timestamp = float(match.group(1))
        gray = cv2.cvtColor(cv2.resize(image, (640, 480)), cv2.COLOR_BGR2GRAY)[400:428, 50:250]
        matching = float(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)[0, 0]) >= .85
        sendout = (sendout_template is not None and
                   float(cv2.matchTemplate(gray, sendout_template, cv2.TM_CCOEFF_NORMED)[0, 0]) >= .90)
        image = cv2.resize(image, (640, 360))
        value = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)[50:310, 100:540, 2]
        scene = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        frames.append((timestamp, value, matching, scene, sendout))

    matching_times = [t for t, _, matching, _, _ in frames if matching]
    if not matching_times:
        return None, []
    last_dialogue = matching_times[-1]
    after = [t for t, _, _, _, _ in frames if last_dialogue < t <= last_dialogue + 2.0]
    complete = (len(after) >= 3 and after[-1] - last_dialogue >= 1.8
                and not any(b - a > .35 for a, b in zip([last_dialogue] + after, after)))

    history = []
    hits = []
    diagnostics = []
    previous_scene = None
    scene_changed = False
    transition = None
    for timestamp, value, _, scene, sendout in frames:
        if timestamp <= last_dialogue - .6 or timestamp > last_dialogue + 2.0:
            continue
        if timestamp > last_dialogue and previous_scene is not None:
            change = np.mean(cv2.absdiff(scene, previous_scene))
            if change > 30:
                # A shiny Giratina cuts to a wider shot before sparkling, so keep
                # analysing with a baseline taken from the new scene.
                if not scene_changed:
                    transition = timestamp
                scene_changed = True
                history = []
        # The send-out ball flash follows this dialogue; it is not a shiny effect.
        if timestamp > last_dialogue and sendout:
            break
        previous_scene = scene
        # A stale baseline would confuse camera motion with flashes.
        history = [(t, v) for t, v in history if timestamp - t <= .6]
        if len(history) >= 2:
            baseline = np.median([v for _, v in history[-4:]], axis=0).astype(np.uint8)
            difference = value.astype(np.int16) - baseline.astype(np.int16)
            mask = ((value >= 225) & (difference >= 65)).astype(np.uint8)
            count, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
            sizes = [int(stat[cv2.CC_STAT_AREA]) for stat in stats[1:count]
                     if 3 <= stat[cv2.CC_STAT_AREA] <= 1500]
            pixels = sum(sizes)
            hit = timestamp > last_dialogue and len(sizes) >= 12 and pixels >= 900
            if timestamp > last_dialogue:
                diagnostics.append((timestamp, len(sizes), pixels, hit))
            if hit:
                hits.append(timestamp)
        history.append((timestamp, value))
    sendout_times = ([t for t, _, _, _, sendout in frames
                      if sendout and transition <= t <= transition + 1.0]
                     if scene_changed else [])
    if sendout_times:
        # A cut straight to the send-out scene shows the ball flash while the
        # dialogue is still fading in, before the template can match it.
        hits = [t for t in hits if t < transition]
    candidate = any(0 < b - a <= .5 for a, b in zip(hits, hits[1:]))
    if candidate:
        return True, diagnostics
    # A single flash or an unexpected cut cannot rule out a missed effect.
    if hits:
        return None, diagnostics
    if scene_changed:
        before_cut = [t for t in after if t < transition]
        through_sendout = ([t for t, _, _, _, _ in frames if transition <= t <= sendout_times[0]]
                           if sendout_times else [])
        observed = [last_dialogue] + before_cut + through_sendout
        if (len(diagnostics) >= 3 and .2 <= transition - last_dialogue <= 1.0
                and sendout_times and not any(b - a > .2 for a, b in zip(observed, observed[1:]))):
            return False, diagnostics
    return (None if scene_changed or not complete else False), diagnostics
