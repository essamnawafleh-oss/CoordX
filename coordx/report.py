"""Printable A4 PDF report: one sheet per parcel, laid out like a survey sketch (مخطط كروكي).

Drawn with QPainter on a QPdfWriter so Arabic text is shaped and ordered by Qt.
The drawing is placed at a standard scale (1:200, 1:500 ...) with a scale bar.
"""
from __future__ import annotations

import datetime
import math
import os

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontMetricsF, QPageLayout, QPageSize, QPainter, QPainterPath, QPdfWriter, QPen

from . import __version__
from .checks import analyze, centroid
from .export_dxf import DxfOptions, build_drawing
from .i18n import lang, tr

DPI = 300
INK = QColor("#1C1F23")
INK2 = QColor("#5B6168")
RULE = QColor("#C9C9C1")
SOFT = QColor("#F3F3EF")
ACCENT = QColor("#0F6B66")
LENGTH_INK = QColor("#0F6B66")
DANGER = QColor("#B3261E")
OK = QColor("#1E7A4C")
SCALES = [50, 100, 200, 250, 500, 750, 1000, 1250, 1500, 2000, 2500, 5000, 10000, 20000, 25000, 50000]
FAMILIES = ["Segoe UI", "Noto Sans Arabic", "Noto Sans", "Arial"]


def mm(v: float) -> float:
    return v * DPI / 25.4


def _font(pt, bold=False):
    f = QFont()
    f.setFamilies(FAMILIES)
    f.setPointSizeF(pt)
    f.setBold(bold)
    return f


def dunum_text(area: float) -> str:
    d = int(area // 1000)
    rest = area - d * 1000
    return tr("dunum_fmt", d=d, m=rest)


class _Sheet:
    """Page geometry helpers in millimetres, mirrored for right-to-left."""

    W, H, M = 210.0, 297.0, 12.0

    def __init__(self, painter: QPainter, rtl: bool):
        self.p = painter
        self.rtl = rtl

    def rect(self, x, y, w, h) -> QRectF:
        """A rect given from the reading-start edge (left in LTR, right in RTL)."""
        if self.rtl:
            x = self.W - x - w
        return QRectF(mm(x), mm(y), mm(w), mm(h))

    def text(self, x, y, w, h, s, font, color=INK, align="start"):
        self.p.setFont(font)
        self.p.setPen(color)
        flags = {"start": Qt.AlignRight if self.rtl else Qt.AlignLeft, "center": Qt.AlignHCenter,
                 "end": Qt.AlignLeft if self.rtl else Qt.AlignRight}[align] | Qt.AlignVCenter
        self.p.drawText(self.rect(x, y, w, h), flags, s)


def _pick_scale(extent_m: float, paper_mm: float) -> int:
    need = extent_m * 1000 / max(paper_mm, 1)
    return next((s for s in SCALES if s >= need * 1.04), SCALES[-1])


def _draw_parcel(sheet: _Sheet, parcel, rep, frame: QRectF):
    """Draw the parcel into `frame` (device pixels) at a standard scale. Returns the scale."""
    p = sheet.p
    pts = parcel.valid_points()
    xs, ys = [q.x for q in pts], [q.y for q in pts]
    w_m, h_m = max(xs) - min(xs), max(ys) - min(ys)
    fw_mm, fh_mm = frame.width() * 25.4 / DPI, frame.height() * 25.4 / DPI
    scale = max(_pick_scale(w_m, fw_mm - 24), _pick_scale(h_m, fh_mm - 24))
    k = mm(1000 / scale)  # device pixels per metre
    # text 2.4 mm tall on paper, expressed in metres for the shared drawing builder
    h_world = 2.4 * scale / 1000
    ents = build_drawing(parcel, DxfOptions(table=False, text_height=h_world), rep)
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    fx, fy = frame.center().x(), frame.center().y()

    def to(x, y):
        return QPointF(fx + (x - cx) * k, fy - (y - cy) * k)

    p.save()
    p.setClipRect(frame)
    p.setRenderHint(QPainter.Antialiasing)
    for e in ents:
        d = e.data
        if e.kind == "poly":
            path = QPainterPath(to(*d["pts"][0]))
            for x, y in d["pts"][1:]:
                path.lineTo(to(x, y))
            if d["closed"]:
                path.closeSubpath()
            p.setPen(QPen(INK, mm(0.45), Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            p.setBrush(QColor(15, 107, 102, 18))
            p.drawPath(path)
            p.setBrush(Qt.NoBrush)
    for e in ents:
        d = e.data
        if e.kind == "point":
            c = to(d["x"], d["y"])
            p.setPen(QPen(INK, mm(0.25)))
            p.setBrush(QColor("white"))
            p.drawEllipse(c, mm(0.9), mm(0.9))
        elif e.kind == "text":
            color = {"LENGTHS": LENGTH_INK, "AREA": INK, "POINT_NO": INK}.get(e.layer, INK)
            hp = d["height"] * 1000 / scale  # paper mm
            f = _font(1)
            f.setPixelSize(max(int(mm(hp) / 0.72), 1))
            f.setBold(e.layer in ("POINT_NO", "AREA"))
            fm = QFontMetricsF(f)
            c = to(*d["pos"])
            p.save()
            p.translate(c)
            p.rotate(-d["rotation"])
            p.setFont(f)
            p.setPen(color)
            tw = fm.horizontalAdvance(d["text"])
            p.drawText(QPointF(-tw / 2, fm.capHeight() / 2), d["text"])
            p.restore()
    p.restore()
    return scale


def _north_arrow(p: QPainter, x, y):
    p.save()
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(INK)
    path = QPainterPath(QPointF(x, y))
    path.lineTo(x - mm(2.6), y + mm(8))
    path.lineTo(x, y + mm(6))
    path.closeSubpath()
    p.drawPath(path)
    p.setBrush(QColor("white"))
    p.setPen(QPen(INK, mm(0.2)))
    path = QPainterPath(QPointF(x, y))
    path.lineTo(x + mm(2.6), y + mm(8))
    path.lineTo(x, y + mm(6))
    path.closeSubpath()
    p.drawPath(path)
    p.setFont(_font(8, True))
    p.setPen(INK)
    p.drawText(QRectF(x - mm(4), y + mm(8.5), mm(8), mm(4)), Qt.AlignCenter, "N")
    p.restore()


def _scale_bar(p: QPainter, x, y, scale):
    """Bar of a round length close to 40 mm on paper, alternating segments."""
    target_m = 40 * scale / 1000
    nice = next(v for v in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000) if v >= target_m / 4)
    seg_mm = nice * 1000 / scale
    p.save()
    p.setPen(QPen(INK, mm(0.2)))
    for i in range(4):
        p.setBrush(INK if i % 2 == 0 else QColor("white"))
        p.drawRect(QRectF(x + mm(seg_mm * i), y, mm(seg_mm), mm(1.6)))
    p.setFont(_font(6.5))
    for i in range(5):
        p.drawText(QRectF(x + mm(seg_mm * i) - mm(6), y + mm(2), mm(12), mm(3.5)), Qt.AlignCenter,
                   f"{nice * i:g}")
    p.drawText(QRectF(x + mm(seg_mm * 4) + mm(4), y - mm(0.6), mm(10), mm(3)), Qt.AlignLeft | Qt.AlignVCenter, "m")
    p.restore()


def _table(sheet: _Sheet, x, y, w, row_h, head, rows, widths, styles=None):
    """Draw a simple table; widths are fractions of w. Returns the y after the table."""
    p = sheet.p
    f, fb = _font(7.5), _font(7.5, True)
    p.setPen(Qt.NoPen)
    p.setBrush(SOFT)
    p.drawRect(sheet.rect(x, y, w, row_h))
    cx = x
    for title, fr in zip(head, widths):
        sheet.text(cx + 1.5, y, w * fr - 3, row_h, title, fb, INK2, "start")
        cx += w * fr
    y += row_h
    for r, row in enumerate(rows):
        if r % 2 == 1:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor("#FAFAF8"))
            p.drawRect(sheet.rect(x, y, w, row_h))
        cx = x
        for c, (val, fr) in enumerate(zip(row, widths)):
            color = (styles or {}).get((r, c), INK)
            sheet.text(cx + 1.5, y, w * fr - 3, row_h, val, f, color, "start")
            cx += w * fr
        y += row_h
    p.setPen(QPen(RULE, mm(0.2)))
    p.drawLine(sheet.rect(x, y, w, 0).topLeft(), sheet.rect(x, y, w, 0).topRight())
    return y


def write_report(parcels, path: str):
    writer = QPdfWriter(path)
    writer.setResolution(DPI)
    writer.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait, QMarginsF(0, 0, 0, 0)))
    writer.setTitle("CoordX")
    writer.setCreator(f"CoordX {__version__}")
    p = QPainter(writer)
    rtl = lang() == "ar"
    sheet = _Sheet(p, rtl)
    S = _Sheet
    # plan the pages first so every footer can say "n / total"
    total_pages = 0
    plan = []
    for parcel in parcels:
        if not parcel.valid_points():
            continue
        rep = analyze(parcel)
        n_pts, n_sides = len(parcel.valid_points()), len(rep.sides)
        first_rows = 14 if max(n_pts, n_sides) <= 14 else 20
        plan.append((parcel, rep, first_rows))
        rest = max(n_pts, n_sides) - first_rows
        total_pages += 1 + (max(0, math.ceil(rest / 42)) if rest > 0 else 0)

    page_no = 0
    today = datetime.date.today().isoformat()
    for idx, (parcel, rep, first_rows) in enumerate(plan):
        pts = parcel.valid_points()
        has_z = any(q.z is not None for q in pts)
        coord_rows = [[q.no, f"{q.x:.2f}", f"{q.y:.2f}"] + ([f"{q.z:.2f}" if q.z is not None else ""] if has_z else [])
                      for q in pts]
        side_rows, side_styles = [], {}
        for r, s in enumerate(rep.sides):
            side_rows.append([f"⁦{s.name}⁩", f"{s.length:.2f}", "" if s.label is None else f"{s.label:.2f}"])
            if s.status == "ok":
                side_styles[(r, 2)] = OK
            elif s.status == "warn":
                side_styles[(r, 1)] = DANGER
        coord_head = [tr("col_no"), "X", "Y"] + (["Z"] if has_z else [])
        coord_w = [0.16, 0.42, 0.42] if not has_z else [0.13, 0.32, 0.32, 0.23]
        side_head = [tr("side"), tr("length"), tr("on_plan")]
        side_w = [0.3, 0.35, 0.35]

        start = 0
        first = True
        while first or start < max(len(coord_rows), len(side_rows)):
            if page_no:
                writer.newPage()
            page_no += 1
            m = S.M
            # header
            sheet.text(m, m, 120, 9, tr("report_title"), _font(17, True), INK, "start")
            sheet.text(m, m + 9, 120, 6, f"{tr('name')}: {parcel.name}" + ("" if first else f"   ·   {tr('continued')}"),
                       _font(10), INK2, "start")
            meta = [today, f"⁦{os.path.basename(parcel.source)}⁩" if parcel.source else tr("method_manual")]
            sheet.text(S.W - m - 70, m + 1, 70, 5, meta[0], _font(8), INK2, "end")
            sheet.text(S.W - m - 70, m + 6, 70, 5, meta[1], _font(8), INK2, "end")
            p.setPen(Qt.NoPen)
            p.setBrush(ACCENT)
            p.drawRect(sheet.rect(m, m + 17, S.W - 2 * m, 0.8))
            y = m + 23

            if first:
                frame_h = 128 if first_rows == 14 else 100
                frame = sheet.rect(m, y, S.W - 2 * m, frame_h)
                p.setPen(QPen(RULE, mm(0.25)))
                p.setBrush(Qt.NoBrush)
                p.drawRect(frame)
                scale = _draw_parcel(sheet, parcel, rep, frame)
                _north_arrow(p, frame.right() - mm(9), frame.top() + mm(5))
                _scale_bar(p, frame.left() + mm(6), frame.bottom() - mm(9), scale)
                p.setFont(_font(7.5))
                p.setPen(INK2)
                p.drawText(QRectF(frame.left() + mm(6), frame.bottom() - mm(15), mm(60), mm(4.5)),
                           Qt.AlignLeft | Qt.AlignVCenter, f"{tr('scale')} 1:{scale}")
                y += frame_h + 5

                # metrics
                metrics = [(f"⁦{rep.area:,.2f}⁩", tr("area_m2")), (dunum_text(rep.area), tr("dunum")),
                           (f"⁦{rep.perimeter:,.2f}⁩", tr("perimeter_m")), (str(len(pts)), tr("points_n"))]
                cw = (S.W - 2 * m) / 4
                for i, (val, cap) in enumerate(metrics):
                    sheet.text(m + i * cw, y, cw - 4, 7, val, _font(12.5, True), INK, "start")
                    sheet.text(m + i * cw, y + 7, cw - 4, 4.5, cap, _font(7.5), INK2, "start")
                y += 13
                if parcel.stated_area:
                    diff = rep.area - parcel.stated_area
                    ok = rep.area_status == "ok"
                    sheet.text(m, y, S.W - 2 * m, 5,
                               tr("report_stated", a=parcel.stated_area, d=diff), _font(8),
                               OK if ok else DANGER, "start")
                    y += 6
                y += 2
                n_rows = first_rows
            else:
                n_rows = 42
            row_h = 5.2
            col_w = (S.W - 2 * m - 8) / 2
            sheet.text(m, y, col_w, 6, tr("coord_table"), _font(9.5, True), INK, "start")
            sheet.text(m + col_w + 8, y, col_w, 6, tr("sides_table"), _font(9.5, True), INK, "start")
            y += 7
            end = start + n_rows
            if coord_rows[start:end]:
                _table(sheet, m, y, col_w, row_h, coord_head, coord_rows[start:end], coord_w)
            if side_rows[start:end]:
                styles = {(r - start, c): v for (r, c), v in side_styles.items() if start <= r < end}
                _table(sheet, m + col_w + 8, y, col_w, row_h, side_head, side_rows[start:end], side_w, styles)
            start = end
            first = False

            # footer
            p.setPen(QPen(RULE, mm(0.2)))
            p.drawLine(sheet.rect(m, S.H - m - 6, S.W - 2 * m, 0).topLeft(),
                       sheet.rect(m, S.H - m - 6, S.W - 2 * m, 0).topRight())
            sheet.text(m, S.H - m - 5, 140, 5, f"CoordX · {tr('dev_label')} {tr('dev_name')}", _font(7.5), INK2, "start")
            sheet.text(S.W - m - 40, S.H - m - 5, 40, 5, f"{page_no} / {total_pages}", _font(7.5), INK2, "end")
    p.end()
    return page_no
