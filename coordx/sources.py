"""Turn input files (images, PDFs, Excel/CSV) into parcels."""
from __future__ import annotations

import os
import tempfile

from .excel_io import read_table_file
from .model import Parcel
from .table_parser import find_tables, side_labels, stated_area
from .textnorm import Token

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}
PDF_EXT = {".pdf"}
TABLE_EXT = {".xlsx", ".xlsm", ".csv", ".txt"}
ALL_EXT = IMAGE_EXT | PDF_EXT | TABLE_EXT

_ocr = None
_tmpdir = None


def _engine():
    global _ocr
    if _ocr is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr = RapidOCR()
    return _ocr


def _temp_dir() -> str:
    global _tmpdir
    if _tmpdir is None:
        _tmpdir = tempfile.mkdtemp(prefix="coordx_")
    return _tmpdir


def _read_image(path: str):
    import cv2
    import numpy as np
    # cv2.imread fails on non-ASCII (e.g. Arabic) Windows paths, so decode from bytes
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("unreadable image")
    return img


def ocr_tokens(img) -> list[Token]:
    """Run OCR on a BGR image; small images are upscaled for better digit recognition."""
    import cv2
    h, w = img.shape[:2]
    scale = 1.0
    if max(h, w) < 1600:
        scale = 1600 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    res, _ = _engine()(img)
    tokens = []
    for box, text, conf in res or []:
        xs = [p[0] / scale for p in box]
        ys = [p[1] / scale for p in box]
        tokens.append(Token(text, min(xs), min(ys), max(xs), max(ys), float(conf)))
    return tokens


def _parcels_from_tokens(tokens, base_name, source, image, page, method) -> list[Parcel]:
    tables = find_tables(tokens)
    labels = side_labels(tokens)
    area = stated_area(tokens) if len(tables) == 1 else None
    out = []
    for i, t in enumerate(tables, 1):
        name = base_name if len(tables) == 1 else f"{base_name}-{i}"
        out.append(Parcel(name=name, points=t.points, source=source, page=page, image=image,
                          labels=labels, stated_area=area, method=method))
    return out


def load_image(path: str) -> list[Parcel]:
    base = os.path.splitext(os.path.basename(path))[0]
    tokens = ocr_tokens(_read_image(path))
    parcels = _parcels_from_tokens(tokens, base, path, path, None, "ocr")
    if not parcels:
        parcels = [Parcel(name=base, source=path, image=path, method="ocr",
                          labels=side_labels(tokens), stated_area=stated_area(tokens))]
    return parcels


def load_pdf(path: str, progress=None) -> list[Parcel]:
    import pymupdf as fitz
    import numpy as np
    base = os.path.splitext(os.path.basename(path))[0]
    out = []
    with fitz.open(path) as doc:
        multi = doc.page_count > 1
        for pno, page in enumerate(doc, 1):
            if progress:
                progress(pno, doc.page_count)
            name = f"{base}-p{pno}" if multi else base
            dpi = 200
            pix = page.get_pixmap(dpi=dpi)
            img_path = os.path.join(_temp_dir(), f"{abs(hash(path))}_{pno}.png")
            pix.save(img_path)
            s = dpi / 72
            words = page.get_text("words")
            tokens = [Token(w[4], w[0] * s, w[1] * s, w[2] * s, w[3] * s, 1.0) for w in words]
            parcels = _parcels_from_tokens(tokens, name, path, img_path, pno, "pdf-text")
            if not parcels:
                # Scanned page: OCR a sharper render
                big = page.get_pixmap(dpi=300)
                arr = np.frombuffer(big.samples, dtype=np.uint8).reshape(big.height, big.width, big.n)
                arr = arr[:, :, :3][:, :, ::-1].copy()  # RGB -> BGR
                tokens = ocr_tokens(arr)
                k = dpi / 300
                for t in tokens:
                    t.x0, t.y0, t.x1, t.y1 = t.x0 * k, t.y0 * k, t.x1 * k, t.y1 * k
                parcels = _parcels_from_tokens(tokens, name, path, img_path, pno, "ocr")
            out.extend(parcels)
    return out


def load_file(path: str, progress=None) -> list[Parcel]:
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXT:
        return load_image(path)
    if ext in PDF_EXT:
        return load_pdf(path, progress)
    if ext in TABLE_EXT:
        return read_table_file(path)
    raise ValueError(f"unsupported file type: {ext}")
