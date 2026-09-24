"""Regression test for parsers/tables.py, built from the exact real-world
table that exposed the bug: a 4-column Educational Qualification table where
naive top-to-bottom reading scrambled results away from their exams, and a
wrapped Institution cell leaked into the next row.
"""
import sys
from pathlib import Path

import fitz
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from parsers.pdf_parser import parse_pdf  # noqa: E402
from parsers.tables import detect_and_reconstruct  # noqa: E402

PAGE_W, PAGE_H = 612, 792


def _make_pdf(tmp_path: Path, rows: list[list[str]], col_x: list[float]) -> str:
    """rows: list of [examination, board, institution, result] where
    institution may be a list of strings to simulate a wrapped multi-line cell.
    """
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    headers = ["Examination", "Board/University", "Institution", "Result"]
    y = 60.0
    for h, x in zip(headers, col_x):
        page.insert_text((x, y), h, fontsize=10, fontname="hebo")  # bold-ish
    y += 25.0
    for row in rows:
        row_top = y
        exam, board, institution_lines, result = row
        page.insert_text((col_x[0], y), exam, fontsize=10)
        page.insert_text((col_x[1], y), board, fontsize=10)
        page.insert_text((col_x[3], y), result, fontsize=10)
        iy = y
        for line in institution_lines:
            page.insert_text((col_x[2], iy), line, fontsize=10)
            iy += 14.0
        y = max(y, iy) + 25.0
    path = tmp_path / "table.pdf"
    doc.save(str(path))
    return str(path)


def test_wrapped_institution_cell_stays_with_its_own_row(tmp_path):
    """The exact real bug: a 4-line wrapped Institution cell must stay
    attached to ITS row, not leak into the next one just because its last
    line lands geometrically closer to the following row's start.
    """
    col_x = [50, 160, 280, 420]
    rows = [
        ["B.Tech CSE", "DYPATU",
         ["D. Y. Patil", "Agriculture &", "Technical", "University, Talsande"],
         "CGPA: 7.50"],
        ["HSC", "State Board", ["Shivraj Vidyalaya,", "Murgud"], "60%"],
        ["SSC", "State Board", ["New English", "Medium School,", "Murgud"], "76%"],
    ]
    path = _make_pdf(tmp_path, rows, col_x)
    doc = parse_pdf(path)

    start = next(i for i, l in enumerate(doc.lines) if l.text == "Examination")
    result = detect_and_reconstruct(doc.lines[start:])
    assert result is not None
    assert len(result) == 3

    assert "B.Tech CSE" in result[0] and "CGPA: 7.50" in result[0]
    assert "D. Y. Patil Agriculture & Technical University, Talsande" in result[0]
    # must NOT have leaked into row 2
    assert "University, Talsande" not in result[1]

    assert "HSC" in result[1] and "60%" in result[1]
    assert "Shivraj Vidyalaya, Murgud" in result[1]

    assert "SSC" in result[2] and "76%" in result[2]


def test_non_table_section_returns_none(tmp_path):
    """A normal prose section (no bold multi-column header) must not be
    mistaken for a table."""
    doc = fitz.open()
    page = doc.new_page(width=PAGE_W, height=PAGE_H)
    for i, text in enumerate([
        "Computer Science Engineering student with a growing specialization",
        "in Data Analytics and a strong foundation in Python, SQL.",
    ]):
        page.insert_text((50, 60 + i * 16), text, fontsize=10)
    path = tmp_path / "prose.pdf"
    doc.save(str(path))

    doc2 = parse_pdf(str(path))
    assert detect_and_reconstruct(doc2.lines) is None
