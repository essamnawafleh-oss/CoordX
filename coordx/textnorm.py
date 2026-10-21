"""Text normalisation and number extraction for OCR / PDF tokens."""
from __future__ import annotations

import re
from dataclasses import dataclass

_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
# Letters OCR often returns instead of digits, only fixed when they sit between digits
_CONFUSED = re.compile(r"(?<=[\d.])[OoQDlI|](?=[\d.])")
_CONFUSED_MAP = {"O": "0", "o": "0", "Q": "0", "D": "0", "l": "1", "I": "1", "|": "1"}
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
_UNIT = r"(?:m2|m²|sqm|sq\.?m|م2|م²|م٢|متر\s*مربع)"
AREA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*" + _UNIT + r"|" + _UNIT + r"\s*(\d+(?:\.\d+)?)", re.I)


def normalize(text: str) -> str:
    """Return text with ASCII digits and '.' decimals. Keeps the same length."""
    t = text.translate(_DIGITS)
    t = t.replace("٫", ".").replace("٬", " ").replace("،", " ")
    t = _CONFUSED.sub(lambda m: _CONFUSED_MAP[m.group()], t)
    # 351309,08 -> 351309.08 ; 351,309.08 -> 351 309.08 would be wrong, so drop thousands commas
    if "." in t:
        t = re.sub(r"(?<=\d),(?=\d{3}\b)", " ", t)
    t = re.sub(r"(?<=\d),(?=\d{1,4}\b)", ".", t)
    return t


@dataclass
class Token:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    conf: float = 1.0

    @property
    def h(self) -> float:
        return self.y1 - self.y0

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2


@dataclass
class Num:
    value: float
    text: str
    x0: float
    x1: float
    y0: float
    y1: float
    conf: float
    token: int  # index of the token it came from

    @property
    def int_digits(self) -> int:
        return len(self.text.split(".")[0])

    @property
    def decimals(self) -> int:
        return len(self.text.split(".")[1]) if "." in self.text else 0

    @property
    def xc(self) -> float:
        return (self.x0 + self.x1) / 2

    @property
    def yc(self) -> float:
        return (self.y0 + self.y1) / 2

    @property
    def h(self) -> float:
        return self.y1 - self.y0


def extract_numbers(tokens: list[Token]) -> list[Num]:
    """Split every token into numbers, estimating each number's horizontal position."""
    out = []
    for i, tok in enumerate(tokens):
        t = normalize(tok.text)
        n = max(len(t), 1)
        w = tok.x1 - tok.x0
        for m in NUM_RE.finditer(t):
            out.append(Num(
                value=float(m.group()), text=m.group(),
                x0=tok.x0 + w * m.start() / n, x1=tok.x0 + w * m.end() / n,
                y0=tok.y0, y1=tok.y1, conf=tok.conf, token=i,
            ))
    return out


def find_area(tokens: list[Token]) -> float | None:
    """Area written with an m2 unit, e.g. '3987M2' or '987.00 م2'. Largest wins."""
    best = None
    # join tokens on the same line, "123.45" and "m2" are often separate words
    lines: list[list[Token]] = []
    for tok in sorted(tokens, key=lambda t: t.yc):
        if lines and abs(tok.yc - lines[-1][0].yc) < 0.5 * max(tok.h, 1):
            lines[-1].append(tok)
        else:
            lines.append([tok])
    texts = [t.text for t in tokens] + [" ".join(t.text for t in sorted(ln, key=lambda t: t.x0)) for ln in lines]
    for text in texts:
        for m in AREA_RE.finditer(normalize(text)):
            v = float(m.group(1) or m.group(2))
            if v > 0 and (best is None or v > best):
                best = v
    return best


def parse_float(text) -> float | None:
    """Parse a user/Excel value into float; None when empty or not a number."""
    if text is None:
        return None
    if isinstance(text, (int, float)):
        return float(text)
    t = normalize(str(text)).strip().replace(" ", "")
    if not t:
        return None
    try:
        return float(t)
    except ValueError:
        return None
