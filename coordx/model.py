"""Data model shared by readers, checks, UI and exporters."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Point:
    no: str = ""
    x: float | None = None
    y: float | None = None
    z: float | None = None
    # OCR confidence per field ("no", "x", "y", "z"); missing means 1.0
    conf: dict = field(default_factory=dict)
    # Location of the row in the source image (pixels): (x0, y0, x1, y1)
    bbox: tuple | None = None
    # Notes left by the reader, e.g. a merged number that was split
    notes: list = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.x is not None and self.y is not None


@dataclass
class Parcel:
    name: str
    points: list[Point] = field(default_factory=list)
    source: str = ""          # original file path
    page: int | None = None   # PDF page (1-based) or None
    image: str | None = None  # image shown in the review panel
    # Numbers found elsewhere in the source (side lengths written on the plan)
    labels: list[float] = field(default_factory=list)
    stated_area: float | None = None
    method: str = ""          # "ocr", "pdf-text", "excel", "manual"

    def valid_points(self) -> list[Point]:
        return [p for p in self.points if p.valid]
