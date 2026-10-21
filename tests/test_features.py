"""Rotation/straightening, DXF import, PDF report and AutoCAD lookup."""
import os

import pytest

from coordx.export_dxf import DxfOptions, export_dxf
from coordx.model import Parcel, Point

PLAN = [(351309.08, 351899.71), (351285.98, 351906.96), (351271.10, 351906.58), (351258.54, 351898.09),
        (351245.93, 351887.28), (351240.58, 351880.73)]


def _table_image(path, angle=0.0):
    """A white page with a printed coordinate table, optionally tilted."""
    import pymupdf
    doc = pymupdf.open()
    page = doc.new_page()
    for i, (x, y) in enumerate(PLAN):
        yy = 100 + 16 * i
        page.insert_text((60, yy), str(i + 1), fontsize=10)
        page.insert_text((90, yy), f"{x:.2f}", fontsize=10)
        page.insert_text((180, yy), f"{y:.2f}", fontsize=10)
    page.get_pixmap(dpi=150).save(path)
    if angle:
        from coordx.imageops import rotate_image
        return rotate_image(path, angle)
    return path


def test_rotate_and_estimate_skew(tmp_path):
    from coordx.imageops import estimate_skew
    tilted = _table_image(str(tmp_path / "t.png"), 5)
    assert abs(estimate_skew(tilted) + 5) <= 0.6


def test_read_region_only_reads_inside(tmp_path):
    from coordx.imageops import read_tables
    img = _table_image(str(tmp_path / "t.png"))
    # the table sits around x 110-480, y 180-420 px at 150 dpi
    tables = read_tables(img, (100, 170, 500, 430))
    assert len(tables) == 1 and [(p.x, p.y) for p in tables[0].points] == PLAN
    assert read_tables(img, (600, 900, 900, 1100)) == []


def test_dxf_roundtrip_and_points(tmp_path):
    import ezdxf
    from coordx.dxf_import import read_dxf
    a = Parcel("30", [Point(str(i), x, y) for i, (x, y) in enumerate(PLAN, 1)])
    b = Parcel("31", [Point(str(i), x + 100, y) for i, (x, y) in enumerate(PLAN, 1)])
    export_dxf([a, b], str(tmp_path / "rt.dxf"), DxfOptions())
    got = read_dxf(str(tmp_path / "rt.dxf"))
    assert [g.name for g in got] == ["30", "31"]
    assert [(p.no, p.x, p.y) for p in got[0].points] == [(str(i), x, y) for i, (x, y) in enumerate(PLAN, 1)]

    doc = ezdxf.new()
    msp = doc.modelspace()
    for i, (x, y) in reversed(list(enumerate(PLAN, 1))):
        msp.add_point((x, y, 800 + i))
        msp.add_text(str(i), height=0.8).set_placement((x + 0.5, y + 0.5))
    doc.saveas(tmp_path / "pts.dxf")
    pts = read_dxf(str(tmp_path / "pts.dxf"))[0].points
    assert [p.no for p in pts] == [str(i) for i in range(1, 7)] and pts[0].z == 801


def test_dwg_is_refused(tmp_path):
    from coordx.sources import DwgError, load_file
    f = tmp_path / "a.dwg"
    f.write_bytes(b"AC1032")
    with pytest.raises(DwgError):
        load_file(str(f))


def test_pdf_report_pages(tmp_path, qapp):
    import pymupdf
    from coordx.report import dunum_text, write_report
    big = Parcel("big", [Point(str(i), 200000 + i * 3.0, 600000 + (i % 2) * 5.0) for i in range(1, 41)])
    small = Parcel("30", [Point(str(i), x, y) for i, (x, y) in enumerate(PLAN, 1)])
    out = tmp_path / "r.pdf"
    n = write_report([small, big], str(out))
    with pymupdf.open(out) as doc:
        assert doc.page_count == n == 3
        assert "351309.08" in doc[0].get_text()
    assert dunum_text(3987.0).startswith("3")


def test_find_acad_prefers_saved_path(tmp_path):
    from coordx.autocad import find_acad
    exe = tmp_path / "acad.exe"
    exe.write_text("")
    assert find_acad(str(exe)) == str(exe)
