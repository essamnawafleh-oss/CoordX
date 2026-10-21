"""Find coordinate tables in positioned text tokens (from OCR or a digital PDF).

The idea: coordinates are long numbers (4+ integer digits). We group them into
rows by vertical position, rows into tables by horizontal position and spacing,
and then read the point number, X, Y and (optionally) Z of every row.
"""
from __future__ import annotations

import re
from collections import Counter
from statistics import median

from .model import Point
from .textnorm import Num, Token, extract_numbers, find_area, normalize

MIN_COORD_DIGITS = 4

_HEADER_WORDS = {
    "x": ("x", "e", "east", "easting", "eastings", "شرقي", "الشرقي", "شرق", "سيني", "السيني"),
    "y": ("y", "n", "north", "northing", "northings", "شمالي", "الشمالي", "شمال", "صادي", "الصادي"),
    "z": ("z", "h", "elev", "elevation", "level", "منسوب", "المنسوب", "ارتفاع", "الارتفاع"),
}


class Table:
    def __init__(self, points: list[Point], roles_from_header: bool):
        self.points = points
        self.roles_from_header = roles_from_header


def _cluster_1d(values: list[float], tol: float) -> list[list[int]]:
    """Group indices of values whose sorted neighbours are closer than tol."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    groups: list[list[int]] = []
    for i in order:
        if groups and values[i] - values[groups[-1][-1]] <= tol:
            groups[-1].append(i)
        else:
            groups.append([i])
    return groups


def _rows(nums: list[Num]) -> list[list[Num]]:
    if not nums:
        return []
    h = median(n.h for n in nums) or 10
    rows: list[list[Num]] = []
    for n in sorted(nums, key=lambda n: n.yc):
        if rows:
            ref = sum(m.yc for m in rows[-1]) / len(rows[-1])
            if abs(n.yc - ref) < 0.55 * h:
                rows[-1].append(n)
                continue
        rows.append([n])
    for r in rows:
        r.sort(key=lambda n: n.x0)
    return rows


def _header_roles(tokens: list[Token], col_x: list[float], top: float, row_h: float, col_w: float) -> dict:
    """Map column index -> 'x'/'y'/'z' from header words just above the table."""
    roles = {}
    for tok in tokens:
        if not (top - 3.5 * row_h <= tok.yc < top - 0.3 * row_h):
            continue
        word = re.sub(r"[\s:.\-()\[\]]", "", normalize(tok.text)).lower()
        if not word:
            continue
        for role, words in _HEADER_WORDS.items():
            if word in words or (len(word) > 2 and any(word.startswith(w) for w in words if len(w) > 2)):
                xc = (tok.x0 + tok.x1) / 2
                ci = min(range(len(col_x)), key=lambda i: abs(col_x[i] - xc))
                if abs(col_x[ci] - xc) < col_w:
                    roles.setdefault(ci, role)
    if len(set(roles.values())) != len(roles):
        return {}
    return roles


def find_tables(tokens: list[Token]) -> list[Table]:
    nums = extract_numbers(tokens)
    coords = [n for n in nums if n.int_digits >= MIN_COORD_DIGITS]
    if len(coords) < 4:
        return []
    used = {id(n) for n in coords}
    others = [n for n in nums if id(n) not in used]

    coord_w = median(n.x1 - n.x0 for n in coords)
    # A text line can cross several tables side by side: cut it at wide gaps
    rows = []
    for r in _rows(coords):
        seg = [r[0]]
        for a, b in zip(r, r[1:]):
            if b.x0 - a.x1 > 2 * coord_w:
                rows.append(seg)
                seg = []
            seg.append(b)
        rows.append(seg)
    rows = [r for r in rows if len(r) >= 2]
    if not rows:
        return []
    row_h = median(n.h for r in rows for n in r)

    # Tables side by side: cluster rows by the position of their first coordinate
    tables_rows: list[list[list[Num]]] = []
    for grp in _cluster_1d([r[0].xc for r in rows], 0.6 * coord_w):
        g = sorted((rows[i] for i in grp), key=lambda r: r[0].yc)
        gaps = [b[0].yc - a[0].yc for a, b in zip(g, g[1:])]
        step = median(gaps) if gaps else row_h * 1.5
        cur = [g[0]]
        for a, b in zip(g, g[1:]):
            if b[0].yc - a[0].yc > max(2.5 * step, 2 * row_h):
                tables_rows.append(cur)
                cur = []
            cur.append(b)
        tables_rows.append(cur)

    result = []
    for trows in tables_rows:
        if len(trows) < 2:
            continue
        result.extend(_build_tables(trows, others, tokens, coord_w, row_h))
    return result


def _build_tables(trows, others, tokens, coord_w, row_h) -> list[Table]:
    # Columns of long numbers
    all_c = [n for r in trows for n in r]
    col_groups = _cluster_1d([n.xc for n in all_c], 0.6 * coord_w)
    col_x = sorted(sum(all_c[i].xc for i in g) / len(g) for g in col_groups
                   if len(g) >= max(2, len(trows) * 0.3))
    x_left = min(n.x0 for n in all_c)
    x_right = max(n.x1 for n in all_c)

    # Extra decimal column (elevations have fewer digits, e.g. 845.32)
    extra = [n for n in others
             if n.decimals >= 1 and n.int_digits <= 4 and x_right - coord_w * 0.2 < n.x0 < x_right + 2.5 * coord_w
             and any(abs(n.yc - r[0].yc) < 0.55 * row_h for r in trows)]
    if extra:
        for g in _cluster_1d([n.xc for n in extra], 0.6 * coord_w):
            if len(g) >= len(trows) * 0.5:
                col_x.append(sum(extra[i].xc for i in g) / len(g))
                break
    col_x.sort()
    if len(col_x) < 2:
        return []

    top = min(n.y0 for n in all_c)
    roles = _header_roles(tokens, col_x, top, row_h, coord_w)
    from_header = "x" in roles.values() and "y" in roles.values()
    if not from_header:
        roles = {0: "x", 1: "y"}
        if len(col_x) >= 3:
            roles[2] = "z"

    # Typical digit count of each column, used to split "13351276.80" into 13 | 351276.80
    def col_of(n: Num) -> int:
        return min(range(len(col_x)), key=lambda i: abs(col_x[i] - n.xc))

    digits = {}
    for ci in range(len(col_x)):
        cnt = Counter(n.int_digits for r in trows for n in r if col_of(n) == ci)
        if cnt:
            digits[ci] = cnt.most_common(1)[0][0]

    # Point numbers sit in a column just left (or, in right-to-left tables, right) of the coordinates
    gap = coord_w * 0.8

    def label_cands(yc, side):
        return [n for n in others if n.decimals == 0 and n.int_digits <= 4
                and abs(n.yc - yc) < 0.55 * row_h
                and (x_left - gap < n.x1 <= x_left + coord_w * 0.1 if side == "left"
                     else x_right - coord_w * 0.1 <= n.x0 < x_right + gap)]

    def row_y(r):
        return sum(n.yc for n in r) / len(r)

    hits = {s: sum(1 for r in trows if label_cands(row_y(r), s)) for s in ("left", "right")}
    label_side = "right" if hits["right"] > hits["left"] else "left"

    parsed = []  # (Point, label int|None)
    for r in trows:
        yc = sum(n.yc for n in r) / len(r)
        row_nums = list(r) + [n for n in extra if abs(n.yc - yc) < 0.55 * row_h]
        p = Point()
        label = None
        notes = []
        for n in row_nums:
            ci = col_of(n)
            if abs(col_x[ci] - n.xc) > coord_w:
                continue
            role = roles.get(ci)
            if role is None or getattr(p, role) is not None:
                continue
            text, value = n.text, n.value
            want = digits.get(ci)
            if want and n.int_digits > want and n.int_digits - want <= 3:
                cut = n.int_digits - want
                if label is None:
                    label = int(text[:cut])
                text = text[cut:]
                value = float(text)
                notes.append("split")
            setattr(p, role, value)
            p.conf[role] = n.conf
        # Point number: a short integer on the same row, just left or right of the table
        if label is None:
            cands = label_cands(yc, label_side)
            if cands:
                best = min(cands, key=lambda n: min(abs(n.x1 - x_left), abs(n.x0 - x_right)))
                label = int(best.value)
                p.conf["no"] = best.conf
        xs = [n.x0 for n in r] + [n.x1 for n in r]
        p.bbox = (min(xs) - coord_w * 0.4, min(n.y0 for n in r), max(xs), max(n.y1 for n in r))
        p.notes = notes
        parsed.append((p, label))

    # Split where numbering restarts at 1 (two tables stacked in one column)
    groups = [[]]
    for k, (p, label) in enumerate(parsed):
        prev = next((lb for _, lb in reversed(groups[-1]) if lb is not None), None)
        nxt = parsed[k + 1][1] if k + 1 < len(parsed) else None
        if (label == 1 and prev is not None and prev >= 2 and len(groups[-1]) >= 2
                and nxt in (None, 2)):
            groups.append([])
        groups[-1].append((p, label))

    tables = []
    for g in groups:
        if len(g) < 2:
            continue
        _number_points(g)
        tables.append(Table([p for p, _ in g], from_header))
    return tables


def _number_points(group):
    """Use the OCR'd numbers when they follow a sequence, filling or fixing the rest."""
    labelled = [(i, lb) for i, (_, lb) in enumerate(group) if lb is not None]
    start = None
    if labelled:
        cnt = Counter(lb - i for i, lb in labelled)
        s, votes = cnt.most_common(1)[0]
        if votes >= max(2, len(labelled) * 0.5) or len(labelled) == 1:
            start = s
    if start is None and not labelled:
        start = 1
    for i, (p, lb) in enumerate(group):
        if start is not None:
            p.no = str(start + i)
            if lb is not None and lb != start + i:
                p.conf["no"] = min(p.conf.get("no", 1.0), 0.5)
        else:
            p.no = str(lb) if lb is not None else ""


def side_labels(tokens: list[Token]) -> list[float]:
    """Short decimal numbers anywhere on the page (candidate side lengths)."""
    return [n.value for n in extract_numbers(tokens)
            if n.decimals >= 1 and n.int_digits < MIN_COORD_DIGITS and n.value > 0]


def stated_area(tokens: list[Token]) -> float | None:
    return find_area(tokens)
