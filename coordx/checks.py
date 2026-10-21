"""Automatic checks on a parcel: side lengths vs. labels on the plan, area, outliers."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from statistics import median

from .model import Parcel

LOW_CONF = 0.85
LABEL_TOL = 0.03       # metres; labels on plans are rounded to 2 decimals
AREA_TOL = 0.01        # 1 %


@dataclass
class Side:
    i: int
    j: int
    name: str
    length: float
    label: float | None = None
    status: str = "none"   # ok: matches a number on the plan, warn: suspicious, none: nothing to compare


@dataclass
class Report:
    sides: list[Side] = field(default_factory=list)
    area: float = 0.0
    perimeter: float = 0.0
    area_status: str = "none"   # ok / warn / none
    area_diff: float | None = None
    # (row, field) -> (level, message key, extra)
    cell_flags: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)  # (level, key, kwargs)

    @property
    def issue_count(self) -> int:
        n = sum(1 for lv, _, _ in self.cell_flags.values() if lv == "error")
        n += sum(1 for s in self.sides if s.status == "warn")
        n += 1 if self.area_status == "warn" else 0
        n += sum(1 for lv, _, _ in self.messages if lv == "error")
        return n


def polygon_area(pts) -> float:
    n = len(pts)
    if n < 3:
        return 0.0
    return abs(sum(pts[k][0] * pts[(k + 1) % n][1] - pts[(k + 1) % n][0] * pts[k][1] for k in range(n))) / 2


def centroid(pts):
    n = len(pts)
    a = cx = cy = 0.0
    for k in range(n):
        x0, y0 = pts[k]
        x1, y1 = pts[(k + 1) % n]
        c = x0 * y1 - x1 * y0
        a += c
        cx += (x0 + x1) * c
        cy += (y0 + y1) * c
    if abs(a) < 1e-9:
        return (sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n)
    return (cx / (3 * a), cy / (3 * a))


def _segments_cross(p1, p2, p3, p4) -> bool:
    def orient(a, b, c):
        v = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        return 0 if abs(v) < 1e-9 else (1 if v > 0 else -1)
    return (orient(p1, p2, p3) * orient(p1, p2, p4) < 0 and orient(p3, p4, p1) * orient(p3, p4, p2) < 0)


def analyze(parcel: Parcel) -> Report:
    rep = Report()
    rows = [(k, p) for k, p in enumerate(parcel.points)]

    # Missing values and low OCR confidence
    for k, p in rows:
        for f in ("x", "y"):
            if getattr(p, f) is None:
                rep.cell_flags[(k, f)] = ("error", "flag_missing", {})
        for f, c in p.conf.items():
            if c < LOW_CONF and (k, f) not in rep.cell_flags:
                rep.cell_flags[(k, f)] = ("warn", "flag_low_conf", {"c": round(c * 100)})
        if "split" in p.notes and (k, "no") not in rep.cell_flags:
            rep.cell_flags[(k, "no")] = ("warn", "flag_split", {})

    valid = [(k, p) for k, p in rows if p.valid]
    if len(valid) < 2:
        return rep

    # Digit-count and distance outliers (typo like 351528 instead of 351258)
    for f in ("x", "y"):
        vals = [getattr(p, f) for _, p in valid]
        digits = median(len(str(int(abs(v)))) for v in vals)
        for k, p in valid:
            if len(str(int(abs(getattr(p, f))))) != digits:
                rep.cell_flags[(k, f)] = ("error", "flag_digits", {})
    pts = [(p.x, p.y) for _, p in valid]
    cx, cy = sum(x for x, _ in pts) / len(pts), sum(y for _, y in pts) / len(pts)
    dists = [math.hypot(x - cx, y - cy) for x, y in pts]
    md = median(dists)
    if md > 0:
        for (k, p), d in zip(valid, dists):
            if d > 6 * md and d - md > 20:
                for f in ("x", "y"):
                    rep.cell_flags.setdefault((k, f), ("error", "flag_far", {}))

    # Sides
    n = len(valid)
    labels = parcel.labels
    lengths = []
    for a in range(n):
        b = (a + 1) % n
        if n == 2 and b == 0:
            break
        (ka, pa), (kb, pb) = valid[a], valid[b]
        length = math.hypot(pb.x - pa.x, pb.y - pa.y)
        side = Side(ka, kb, f"{pa.no or ka + 1}-{pb.no or kb + 1}", length)
        if labels:
            best = min(labels, key=lambda v: abs(v - length))
            if abs(best - length) <= max(LABEL_TOL, length * 0.0005):
                side.label, side.status = best, "ok"
        lengths.append(length)
        rep.sides.append(side)
        if length < 1e-6:
            rep.cell_flags[(kb, "x")] = ("error", "flag_duplicate", {})
            rep.cell_flags[(kb, "y")] = ("error", "flag_duplicate", {})
    rep.perimeter = sum(lengths)

    # A side much longer than the rest usually means a mistyped coordinate
    if len(lengths) >= 4:
        ml = median(lengths)
        for s in rep.sides:
            if s.status != "ok" and ml > 0 and s.length > 8 * ml:
                s.status = "warn"

    if n >= 3:
        rep.area = polygon_area(pts)
        # self intersection
        segs = [(pts[a], pts[(a + 1) % n]) for a in range(n)]
        for a in range(n):
            for b in range(a + 2, n):
                if a == 0 and b == n - 1:
                    continue
                if _segments_cross(*segs[a], *segs[b]):
                    rep.messages.append(("error", "msg_self_cross",
                                         {"a": rep.sides[a].name, "b": rep.sides[b].name}))
        stated = parcel.stated_area
        if stated:
            rep.area_diff = rep.area - stated
            rep.area_status = "ok" if abs(rep.area_diff) <= stated * AREA_TOL else "warn"
        elif labels and rep.area > 0:
            best = min(labels, key=lambda v: abs(v - rep.area))
            if abs(best - rep.area) <= rep.area * 0.002:
                rep.area_status = "ok"
                rep.area_diff = rep.area - best
    return rep
