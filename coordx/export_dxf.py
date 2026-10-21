"""Write parcels to an AutoCAD DXF drawing."""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import ezdxf
from ezdxf.enums import TextEntityAlignment

from .checks import analyze, centroid
from .model import Parcel


@dataclass
class DxfOptions:
    points: bool = True
    numbers: bool = True
    boundary: bool = True
    lengths: bool = True
    table: bool = True
    area: bool = True
    text_height: float | None = None  # None = automatic from the parcel size


LAYERS = {  # name: ACI colour
    "POINTS": 1, "POINT_NO": 7, "BOUNDARY": 3, "LENGTHS": 4, "TABLE": 8, "AREA": 2,
}


def _layer_prefix(name: str) -> str:
    s = re.sub(r'[<>/\\":;?*|=`,]', "_", name).strip()
    return (s[:40] + "_") if s else ""


def auto_text_height(parcel: Parcel) -> float:
    pts = parcel.valid_points()
    if len(pts) < 2:
        return 1.0
    w = max(p.x for p in pts) - min(p.x for p in pts)
    h = max(p.y for p in pts) - min(p.y for p in pts)
    raw = max(math.hypot(w, h) / 60, 0.1)
    # round to a "nice" value: 0.1, 0.2, 0.25, 0.5, 1, 1.5, 2, 2.5, 5 ...
    mag = 10 ** math.floor(math.log10(raw))
    for k in (1, 1.5, 2, 2.5, 5, 10):
        if raw <= k * mag:
            return k * mag
    return raw


def _readable(angle: float) -> float:
    a = math.degrees(angle) % 360
    if 90 < a <= 270:
        a -= 180
    return a


def export_dxf(parcels: list[Parcel], path: str, opts: DxfOptions):
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.M
    if "COORDX" not in doc.styles:
        doc.styles.new("COORDX", dxfattribs={"font": "arial.ttf"})
    msp = doc.modelspace()
    multi = len(parcels) > 1
    max_h = 0

    for parcel in parcels:
        pts = parcel.valid_points()
        if not pts:
            continue
        h = opts.text_height or auto_text_height(parcel)
        max_h = max(max_h, h)
        pre = _layer_prefix(parcel.name) if multi else ""
        for lname, color in LAYERS.items():
            if pre + lname not in doc.layers:
                doc.layers.add(pre + lname, color=color)
        L = lambda n: {"layer": pre + n}
        txt = lambda n, extra=None: {"layer": pre + n, "style": "COORDX", **(extra or {})}

        xy = [(p.x, p.y) for p in pts]
        cx, cy = centroid(xy) if len(xy) >= 3 else (sum(x for x, _ in xy) / len(xy), sum(y for _, y in xy) / len(xy))

        if opts.points:
            for p in pts:
                msp.add_point((p.x, p.y, p.z or 0.0), dxfattribs=L("POINTS"))

        if opts.numbers:
            for p in pts:
                dx, dy = p.x - cx, p.y - cy
                d = math.hypot(dx, dy) or 1
                pos = (p.x + dx / d * h * 1.1, p.y + dy / d * h * 1.1)
                msp.add_text(p.no, height=h, dxfattribs=txt("POINT_NO")).set_placement(
                    pos, align=TextEntityAlignment.MIDDLE_CENTER)

        closed = len(xy) >= 3
        if opts.boundary and len(xy) >= 2:
            msp.add_lwpolyline(xy, close=closed, dxfattribs=L("BOUNDARY"))

        if opts.lengths and len(xy) >= 2:
            n = len(xy)
            for a in range(n if closed else n - 1):
                (x0, y0), (x1, y1) = xy[a], xy[(a + 1) % n]
                length = math.hypot(x1 - x0, y1 - y0)
                if length < 1e-6:
                    continue
                mx, my = (x0 + x1) / 2, (y0 + y1) / 2
                nx, ny = -(y1 - y0) / length, (x1 - x0) / length
                if (mx - cx) * nx + (my - cy) * ny < 0:  # put the label outside
                    nx, ny = -nx, -ny
                pos = (mx + nx * h * 0.8, my + ny * h * 0.8)
                msp.add_text(f"{length:.2f}", height=h * 0.8,
                             dxfattribs=txt("LENGTHS", {"rotation": _readable(math.atan2(y1 - y0, x1 - x0))})
                             ).set_placement(pos, align=TextEntityAlignment.MIDDLE_CENTER)

        rep = analyze(parcel)
        if opts.area and closed:
            msp.add_text(parcel.name, height=h * 1.3, dxfattribs=txt("AREA")).set_placement(
                (cx, cy + h * 1.2), align=TextEntityAlignment.MIDDLE_CENTER)
            msp.add_text(f"A = {rep.area:.2f} m2", height=h * 1.3, dxfattribs=txt("AREA")).set_placement(
                (cx, cy - h * 1.2), align=TextEntityAlignment.MIDDLE_CENTER)

        if opts.table:
            _coord_table(msp, parcel, pts, rep, h, txt, L)

    doc.header["$PDMODE"] = 35
    doc.header["$PDSIZE"] = (max_h or 1.0) * 0.6
    doc.header["$TEXTSTYLE"] = "COORDX"
    doc.saveas(path)


def _coord_table(msp, parcel, pts, rep, h, txt, L):
    has_z = any(p.z is not None for p in pts)
    widths = [h * 4, h * 10, h * 10] + ([h * 7] if has_z else [])
    heads = ["No.", "X (E)", "Y (N)"] + (["Z"] if has_z else [])
    rh = h * 2
    x0 = max(p.x for p in pts) + h * 8
    y0 = max(p.y for p in pts)
    total_w = sum(widths)
    rows = [heads] + [[p.no, f"{p.x:.2f}", f"{p.y:.2f}"] + ([f"{p.z:.2f}" if p.z is not None else ""] if has_z else [])
                      for p in pts]

    title_y = y0 + rh * 0.6
    msp.add_text(parcel.name, height=h * 1.2, dxfattribs=txt("TABLE")).set_placement(
        (x0 + total_w / 2, title_y), align=TextEntityAlignment.MIDDLE_CENTER)
    n_rows = len(rows)
    for r in range(n_rows + 1):
        y = y0 - r * rh
        msp.add_line((x0, y), (x0 + total_w, y), dxfattribs=L("TABLE"))
    x = x0
    for w in [0] + widths:
        x += w
        msp.add_line((x, y0), (x, y0 - n_rows * rh), dxfattribs=L("TABLE"))
    for r, row in enumerate(rows):
        x = x0
        for w, val in zip(widths, row):
            msp.add_text(val, height=h, dxfattribs=txt("TABLE")).set_placement(
                (x + w / 2, y0 - r * rh - rh / 2), align=TextEntityAlignment.MIDDLE_CENTER)
            x += w
    y = y0 - n_rows * rh - rh * 0.8
    msp.add_text(f"AREA = {rep.area:.2f} m2", height=h, dxfattribs=txt("TABLE")).set_placement(
        (x0, y), align=TextEntityAlignment.MIDDLE_LEFT)
    msp.add_text(f"PERIMETER = {rep.perimeter:.2f} m", height=h, dxfattribs=txt("TABLE")).set_placement(
        (x0, y - rh), align=TextEntityAlignment.MIDDLE_LEFT)
