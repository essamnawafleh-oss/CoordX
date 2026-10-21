"""Read points back out of an existing DXF drawing.

Each closed polyline becomes a parcel (its vertices, in drawing order). Without
closed polylines, POINT entities (or block inserts, which surveyors often use
for points) become one parcel per layer. Point numbers come from the nearest
short text next to each point, when there is one.
"""
from __future__ import annotations

import math
import os
import re

from .model import Parcel, Point

_NUM_TEXT = re.compile(r"^\s*[A-Za-z]{0,3}\d{1,5}[A-Za-z]?\s*$")


def _texts(msp):
    out = []
    for e in msp.query("TEXT MTEXT"):
        try:
            if e.dxftype() == "TEXT":
                s = e.dxf.text
                p = e.get_placement()[1] if e.get_placement()[0] else e.dxf.insert
                h = e.dxf.height
            else:
                s = e.plain_text()
                p = e.dxf.insert
                h = e.dxf.char_height
        except Exception:
            continue
        if s and _NUM_TEXT.match(s):
            out.append((s.strip(), float(p[0]), float(p[1]), float(h or 1)))
    return out


def _label(x, y, texts, used, reach):
    best, bd = None, None
    for k, (s, tx, ty, h) in enumerate(texts):
        if k in used:
            continue
        d = math.hypot(tx - x, ty - y)
        if d <= max(reach, 3 * h) and (bd is None or d < bd):
            best, bd = k, d
    if best is None:
        return ""
    used.add(best)
    return texts[best][0]


def _typical_size(xy):
    if len(xy) < 2:
        return 1.0
    xs, ys = [p[0] for p in xy], [p[1] for p in xy]
    return max(max(xs) - min(xs), max(ys) - min(ys), 1e-6)


def read_dxf(path: str) -> list[Parcel]:
    import ezdxf
    from ezdxf import recover

    try:
        doc = ezdxf.readfile(path)
    except ezdxf.DXFStructureError:
        doc, _ = recover.readfile(path)
    msp = doc.modelspace()
    base = os.path.splitext(os.path.basename(path))[0]
    texts = _texts(msp)

    # all point-like positions, so polyline vertices can borrow a POINT's Z
    point_xyz = []
    for e in msp.query("POINT"):
        x, y, z = e.dxf.location
        point_xyz.append((float(x), float(y), float(z), e.dxf.layer))
    inserts = [(float(e.dxf.insert[0]), float(e.dxf.insert[1]), float(e.dxf.insert[2]), e.dxf.layer)
               for e in msp.query("INSERT")]

    rings = []
    for e in msp.query("LWPOLYLINE"):
        if e.closed and len(e) >= 3:
            rings.append(([(float(x), float(y)) for x, y in e.get_points("xy")], e.dxf.layer, e.dxf.elevation))
    for e in msp.query("POLYLINE"):
        if e.is_closed and len(e.vertices) >= 3 and not e.is_poly_face_mesh and not e.is_polygon_mesh:
            rings.append(([(float(v.dxf.location[0]), float(v.dxf.location[1])) for v in e.vertices],
                          e.dxf.layer, 0.0))

    parcels = []
    if rings:
        for i, (pts, layer, _elev) in enumerate(rings, 1):
            reach = _typical_size(pts) / 15
            used: set = set()
            out = []
            for k, (x, y) in enumerate(pts, 1):
                z = next((pz for px, py, pz, _ in point_xyz if math.hypot(px - x, py - y) < 1e-3 and pz), None)
                out.append(Point(no=_label(x, y, texts, used, reach) or str(k), x=round(x, 4), y=round(y, 4), z=z))
            name = base if len(rings) == 1 else f"{base}-{i}"
            if layer.upper().endswith("_BOUNDARY"):  # written by CoordX: "<parcel>_BOUNDARY"
                name = layer[:-len("_BOUNDARY")]
            parcels.append(Parcel(name=name, points=out, source=path, method="dxf"))
        return parcels

    src = point_xyz or inserts
    by_layer: dict = {}
    for x, y, z, layer in src:
        by_layer.setdefault(layer, []).append((x, y, z))
    for layer, pts in by_layer.items():
        reach = _typical_size([(x, y) for x, y, _ in pts]) / 15
        used = set()
        out = [Point(no=_label(x, y, texts, used, reach), x=round(x, 4), y=round(y, 4), z=z or None)
               for x, y, z in pts]
        if out and all(p.no.isdigit() for p in out):
            out.sort(key=lambda p: int(p.no))
        for k, p in enumerate(out, 1):
            p.no = p.no or str(k)
        name = base if len(by_layer) == 1 else f"{base}-{layer}"
        parcels.append(Parcel(name=name, points=out, source=path, method="dxf"))
    return parcels
