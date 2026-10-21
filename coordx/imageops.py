"""Image fixes before reading: rotation, automatic straightening, reading a selected region."""
from __future__ import annotations

import os

from .sources import _parcels_from_tokens, _read_image, _temp_dir, ocr_tokens


def _write_image(img, path):
    import cv2
    ok, buf = cv2.imencode(".png", img)
    if not ok:
        raise ValueError("could not encode image")
    buf.tofile(path)  # works with non-ASCII paths, unlike cv2.imwrite on Windows


def rotate_image(path: str, angle: float) -> str:
    """Rotate counter-clockwise by `angle` degrees onto a white canvas big enough to keep every corner."""
    import cv2
    img = _read_image(path)
    a = angle % 360
    if abs(a) < 1e-6:
        return path
    if abs(a - 90) < 1e-6:
        out = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
    elif abs(a - 180) < 1e-6:
        out = cv2.rotate(img, cv2.ROTATE_180)
    elif abs(a - 270) < 1e-6:
        out = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
    else:
        h, w = img.shape[:2]
        m = cv2.getRotationMatrix2D((w / 2, h / 2), a, 1.0)
        cos, sin = abs(m[0, 0]), abs(m[0, 1])
        nw, nh = int(h * sin + w * cos + 0.5), int(h * cos + w * sin + 0.5)
        m[0, 2] += nw / 2 - w / 2
        m[1, 2] += nh / 2 - h / 2
        out = cv2.warpAffine(img, m, (nw, nh), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    base = os.path.splitext(os.path.basename(path))[0]
    dst = os.path.join(_temp_dir(), f"{base}_{abs(hash((path, round(a, 3))))}.png")
    _write_image(out, dst)
    return dst


def estimate_skew(path: str, max_angle: float = 15.0) -> float:
    """Angle (degrees, counter-clockwise) that makes text lines horizontal.

    Projection-profile method: when the page is straight, text rows give the
    sharpest peaks in the per-row ink count.
    """
    import cv2
    import numpy as np
    img = _read_image(path)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    k = 1000 / max(h, w)
    if k < 1:
        gray = cv2.resize(gray, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    hh, ww = ink.shape
    center = (ww / 2, hh / 2)

    def score(angle):
        m = cv2.getRotationMatrix2D(center, angle, 1.0)
        rot = cv2.warpAffine(ink, m, (ww, hh), flags=cv2.INTER_NEAREST, borderValue=0)
        rows = rot.sum(axis=1, dtype=np.float64)
        return float(np.sum(np.diff(rows) ** 2))

    best = max(np.arange(-max_angle, max_angle + 0.01, 0.5), key=score)
    best = max(np.arange(best - 0.5, best + 0.51, 0.1), key=score)
    return round(float(best), 1)


def read_tables(image_path: str, rect=None, name: str = "", source: str = "", page=None):
    """OCR an image, or only `rect` (x0, y0, x1, y1 in image pixels) of it, into parcels.

    Row boxes are returned in the coordinates of the whole image.
    """
    img = _read_image(image_path)
    ox = oy = 0
    if rect is not None:
        h, w = img.shape[:2]
        pad = 6
        x0, y0 = max(0, int(rect[0]) - pad), max(0, int(rect[1]) - pad)
        x1, y1 = min(w, int(rect[2]) + pad), min(h, int(rect[3]) + pad)
        if x1 - x0 < 10 or y1 - y0 < 10:
            return []
        img = img[y0:y1, x0:x1]
        ox, oy = x0, y0
    tokens = ocr_tokens(img)
    for t in tokens:
        t.x0, t.x1, t.y0, t.y1 = t.x0 + ox, t.x1 + ox, t.y0 + oy, t.y1 + oy
    return _parcels_from_tokens(tokens, name, source, image_path, page, "ocr")
