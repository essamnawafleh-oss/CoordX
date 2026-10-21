"""Build the drawing of a parcel and write it to an AutoCAD DXF file.

build_drawing() produces plain entities that both the DXF writer and the
on-screen viewer use, so what the viewer shows is what the DXF contains.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

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


@dataclass
class Ent:
    kind: str    # "point", "text", "poly", "line"
    layer: str
    # point: x, y, z, index | text: text, pos, height, rotation, align ("center"/"left")
    # poly: pts, closed | line: a, b
    data: dict = field(default_factory=dict)


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


def build_drawing(parcel: Parcel, opts: DxfOptions, rep=None) -> list[Ent]:
    """Entities for one parcel. Point entities keep their row index in parcel.points."""
    rows = [(k, p) for k, p in enumerate(parcel.points) if p.valid]
    if not rows:
        return []
    pts = [p for _, p in rows]
    rep = rep or analyze(parcel)
    h = opts.text_height or auto_text_height(parcel)
    out: list[Ent] = []

    def text(layer, s, pos, height, rotation=0.0, align="center"):
        out.append(Ent("text", layer, {"text": s, "pos": pos, "height": height, "rotation": rotation,
                                       "align": align}))

    xy = [(p.x, p.y) for p in pts]
    closed = len(xy) >= 3
    cx, cy = centroid(xy) if closed else (sum(x for x, _ in xy) / len(xy), sum(y for _, y in xy) / len(xy))

    if opts.boundary and len(xy) >= 2:
        out.append(Ent("poly", "BOUNDARY", {"pts": xy, "closed": closed}))

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
            text("LENGTHS", f"{length:.2f}", (mx + nx * h * 0.8, my + ny * h * 0.8), h * 0.8,
                 _readable(math.atan2(y1 - y0, x1 - x0)))

    if opts.points:
        for k, p in rows:
            out.append(Ent("point", "POINTS", {"x": p.x, "y": p.y, "z": p.z or 0.0, "index": k}))

    if opts.numbers:
        for p in pts:
            dx, dy = p.x - cx, p.y - cy
            d = math.hypot(dx, dy) or 1
            text("POINT_NO", p.no, (p.x + dx / d * h * 1.1, p.y + dy / d * h * 1.1), h)

    if opts.area and closed:
        text("AREA", parcel.name, (cx, cy + h * 1.2), h * 1.3)
        text("AREA", f"A = {rep.area:.2f} m2", (cx, cy - h * 1.2), h * 1.3)

    if opts.table:
        out.extend(_coord_table(parcel, pts, rep, h))
    return out


def _coord_table(parcel, pts, rep, h) -> list[Ent]:
    out = []
    has_z = any(p.z is not None for p in pts)
    widths = [h * 4, h * 10, h * 10] + ([h * 7] if has_z else [])
    heads = ["No.", "X (E)", "Y (N)"] + (["Z"] if has_z else [])
    rh = h * 2
    x0 = max(p.x for p in pts) + h * 8
    y0 = max(p.y for p in pts)
    total_w = sum(widths)
    rows = [heads] + [[p.no, f"{p.x:.2f}", f"{p.y:.2f}"] + ([f"{p.z:.2f}" if p.z is not None else ""] if has_z else [])
                      for p in pts]

    def text(s, pos, height, align="center"):
        out.append(Ent("text", "TABLE", {"text": s, "pos": pos, "height": height, "rotation": 0.0, "align": align}))

    text(parcel.name, (x0 + total_w / 2, y0 + rh * 0.6), h * 1.2)
    n_rows = len(rows)
    for r in range(n_rows + 1):
        y = y0 - r * rh
        out.append(Ent("line", "TABLE", {"a": (x0, y), "b": (x0 + total_w, y)}))
    x = x0
    for w in [0] + widths:
        x += w
        out.append(Ent("line", "TABLE", {"a": (x, y0), "b": (x, y0 - n_rows * rh)}))
    for r, row in enumerate(rows):
        x = x0
        for w, val in zip(widths, row):
            text(val, (x + w / 2, y0 - r * rh - rh / 2), h)
            x += w
    y = y0 - n_rows * rh - rh * 0.8
    text(f"AREA = {rep.area:.2f} m2", (x0, y), h, "left")
    text(f"PERIMETER = {rep.perimeter:.2f} m", (x0, y - rh), h, "left")
    return out


def export_dxf(parcels: list[Parcel], path: str, opts: DxfOptions):
    import ezdxf
    from ezdxf.enums import TextEntityAlignment

    align = {"center": TextEntityAlignment.MIDDLE_CENTER, "left": TextEntityAlignment.MIDDLE_LEFT}
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.M
    if "COORDX" not in doc.styles:
        doc.styles.new("COORDX", dxfattribs={"font": "arial.ttf"})
    msp = doc.modelspace()
    multi = len(parcels) > 1
    max_h = 0

    for parcel in parcels:
        ents = build_drawing(parcel, opts)
        if not ents:
            continue
        max_h = max(max_h, opts.text_height or auto_text_height(parcel))
        pre = _layer_prefix(parcel.name) if multi else ""
        for lname, color in LAYERS.items():
            if pre + lname not in doc.layers:
                doc.layers.add(pre + lname, color=color)
        for e in ents:
            attrs = {"layer": pre + e.layer}
            d = e.data
            if e.kind == "point":
                msp.add_point((d["x"], d["y"], d["z"]), dxfattribs=attrs)
            elif e.kind == "poly":
                msp.add_lwpolyline(d["pts"], close=d["closed"], dxfattribs=attrs)
            elif e.kind == "line":
                msp.add_line(d["a"], d["b"], dxfattribs=attrs)
            elif e.kind == "text":
                attrs.update(style="COORDX", rotation=d["rotation"])
                msp.add_text(d["text"], height=d["height"], dxfattribs=attrs).set_placement(
                    d["pos"], align=align[d["align"]])

    doc.header["$PDMODE"] = 35
    doc.header["$PDSIZE"] = (max_h or 1.0) * 0.6
    doc.header["$TEXTSTYLE"] = "COORDX"
    doc.saveas(path)
