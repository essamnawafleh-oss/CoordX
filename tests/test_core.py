import os

import pytest

from coordx.checks import analyze
from coordx.excel_io import read_table_file, write_csv, write_excel
from coordx.export_dxf import DxfOptions, export_dxf
from coordx.model import Parcel, Point
from coordx.table_parser import find_tables
from coordx.textnorm import Token, find_area, normalize, parse_float

PLAN = [(351309.08, 351899.71), (351285.98, 351906.96), (351271.10, 351906.58), (351258.54, 351898.09),
        (351245.93, 351887.28), (351240.58, 351880.73), (351238.48, 351875.22), (351236.16, 351865.31),
        (351235.91, 351855.36), (351240.88, 351842.11), (351245.67, 351831.23), (351253.46, 351821.84),
        (351276.80, 351816.91)]


def table_tokens(rows, x=100, y=100, dy=22, label=True):
    toks = []
    for i, (a, b) in enumerate(rows):
        yy = y + i * dy
        if label:
            toks.append(Token(str(i + 1), x, yy, x + 14, yy + 16))
        toks.append(Token(f"{a:.2f}", x + 24, yy, x + 120, yy + 16))
        toks.append(Token(f"{b:.2f}", x + 130, yy, x + 226, yy + 16))
    return toks


def test_normalize_arabic_digits_and_comma():
    assert normalize("٣٥١٢٨٥٫٩٨") == "351285.98"
    assert parse_float("351309,08") == 351309.08
    assert parse_float("35I309.08") == 351309.08
    assert parse_float("") is None


def test_find_area_variants():
    assert find_area([Token("3987M2", 0, 0, 50, 10)]) == 3987
    assert find_area([Token("123.45", 0, 0, 40, 10), Token("m2", 45, 0, 60, 10)]) == 123.45
    assert find_area([Token("م2", 0, 0, 20, 10), Token("987.00", 25, 0, 60, 10)]) == 987


def test_single_table():
    tables = find_tables(table_tokens(PLAN))
    assert len(tables) == 1
    pts = tables[0].points
    assert [p.no for p in pts] == [str(i) for i in range(1, 14)]
    assert (pts[0].x, pts[0].y) == PLAN[0]


def test_tables_side_by_side_and_stacked():
    a, b = PLAN[:6], PLAN[6:]
    toks = table_tokens(a) + table_tokens(b, x=700) + table_tokens(b, y=400)
    tables = find_tables(toks)
    assert sorted(len(t.points) for t in tables) == [6, 7, 7]


def test_merged_number_is_split():
    toks = table_tokens(PLAN[:-1])
    yy = 100 + 12 * 22
    toks += [Token("13351276.80", 100, yy, 120 + 20, yy + 16), Token("351816.91", 230, yy, 326, yy + 16)]
    pts = find_tables(toks)[0].points
    assert pts[-1].no == "13" and pts[-1].x == 351276.80


def test_checks_match_labels_and_flag_typo():
    p = Parcel("t", [Point(str(i), x, y) for i, (x, y) in enumerate(PLAN, 1)], labels=[24.20, 14.89, 15.16])
    rep = analyze(p)
    assert round(rep.area, 2) == 4262.11
    assert [s.status for s in rep.sides[:3]] == ["ok", "ok", "ok"]
    p.points[3].x = 3512580.54  # extra digit
    assert analyze(p).cell_flags[(3, "x")][0] == "error"


def test_area_vs_stated():
    p = Parcel("t", [Point(str(i), x, y) for i, (x, y) in enumerate(PLAN, 1)], stated_area=3987)
    assert analyze(p).area_status == "warn"
    p.stated_area = 4262
    assert analyze(p).area_status == "ok"


def test_excel_roundtrip_and_exports(tmp_path):
    import openpyxl
    src = tmp_path / "in.xlsx"
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Point", "Northing", "Easting"])
    for i, (x, y) in enumerate(PLAN, 1):
        ws.append([i, y, x])
    wb.save(src)
    parcels = read_table_file(str(src))
    assert len(parcels) == 1 and parcels[0].points[0].x == PLAN[0][0]
    reps = [analyze(p) for p in parcels]
    write_excel(parcels, reps, str(tmp_path / "out.xlsx"))
    write_csv(parcels, str(tmp_path / "out.csv"))
    export_dxf(parcels, str(tmp_path / "out.dxf"), DxfOptions())
    import ezdxf
    doc = ezdxf.readfile(str(tmp_path / "out.dxf"))
    assert len(doc.modelspace().query("POINT")) == 13
    assert len(doc.modelspace().query("LWPOLYLINE")) == 1


def test_csv_semicolon_decimal_comma(tmp_path):
    f = tmp_path / "c.csv"
    f.write_text("1;351309,08;351899,71\n2;351285,98;351906,96\n3;351271,10;351906,58\n")
    pts = read_table_file(str(f))[0].points
    assert pts[1].x == 351285.98 and pts[1].y == 351906.96


@pytest.mark.skipif(not os.environ.get("COORDX_SAMPLE"), reason="needs a sample plan image")
def test_ocr_sample_image():
    from coordx.sources import load_file
    p = load_file(os.environ["COORDX_SAMPLE"])[0]
    assert [(q.x, q.y) for q in p.points] == PLAN
