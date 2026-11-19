"""Experimental Giratina color check based on the central body stripes."""
import re
from pathlib import Path

import cv2
import numpy as np

TEMPLATES = Path(__file__).with_name("templates")
FRAME = re.compile(r'^frame_\d+_([\d.]+)s\.png$')


def dialogue(image, name):
    template = cv2.imread(str(TEMPLATES / name), cv2.IMREAD_GRAYSCALE)
    if template is None:
        return False
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[400:428, 50:250]
    return float(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)[0, 0]) >= .90


def classify_frame(path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'画像を読み込めません: {path}')
    image = cv2.resize(image, (640, 480))
    hsv = cv2.cvtColor(image[190:350, 295:345], cv2.COLOR_BGR2HSV)
    h, s, v = cv2.split(hsv)
    red = (((h < 10) | (h > 170)) & (s > 100) & (v > 65)).mean()
    cyan = ((h >= 80) & (h <= 110) & (s > 90) & (v > 65)).mean()
    # Check the pose before identifying either color.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)[150:385, 245:465]
    templates = [cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
                 for path in sorted(TEMPLATES.glob('pose_*.png'))]
    if len(templates) != 6 or any(template is None for template in templates):
        return 'unknown', red, cyan
    similarity = max(float(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)[0, 0])
                     for template in templates)
    if similarity < .70:
        # The lowered pose exposes the wings before the central stripes.
        bowed_paths = [TEMPLATES / f'bowed_{name}.png' for name in ('142130', '142208', '142225')]
        bowed_templates = [cv2.imread(str(path), cv2.IMREAD_GRAYSCALE) for path in bowed_paths]
        if any(template is None for template in bowed_templates):
            return 'unknown', red, cyan
        bowed_similarity = max(float(cv2.matchTemplate(gray, template, cv2.TM_CCOEFF_NORMED)[0, 0])
                               for template in bowed_templates)
        if bowed_similarity >= .80:
            wing_hsv = cv2.cvtColor(image[150:385, 160:480], cv2.COLOR_BGR2HSV)
            wh, ws, wv = cv2.split(wing_hsv)
            wing_cyan = ((wh >= 80) & (wh <= 110) & (ws > 90) & (wv > 65)).mean()
            if wing_cyan > .03:
                return 'shiny_candidate', red, cyan
        return 'unknown', red, cyan
    if cyan > .05:
        return 'shiny_candidate', red, cyan
    if red > .10 and dialogue(image, 'dialog_encounter.png'):
        return 'normal', red, cyan
    return 'unknown', red, cyan


def is_sendout(path):
    image = cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f'画像を読み込めません: {path}')
    return dialogue(cv2.resize(image, (640, 480)), 'dialog_sendout.png')


def classify_directory(directory):
    paths = []
    for path in sorted(Path(directory).glob('frame_*.png')):
        match = FRAME.match(path.name)
        if match and 8.0 <= float(match.group(1)) <= 12.5:
            paths.append(path)
    results = [(p, *classify_frame(p)) for p in paths]
    states = [result[1] for result in results]
    if 'shiny_candidate' in states:
        return 'shiny_candidate', results
    # Unmatched cyan can be an obscured shiny; never reset on that ambiguity.
    if any(state == 'unknown' and cyan > .05 and not is_sendout(path)
           for path, state, _, cyan in results):
        return 'unknown', results
    if sum(state == 'normal' for state in states) >= 2:
        return 'normal', results
    return 'unknown', results
