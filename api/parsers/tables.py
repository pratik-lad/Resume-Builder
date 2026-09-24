"""Multi-column table reconstruction for resume sections like Educational
Qualification, which are usually rendered as a genuine N-column table
(Examination | Board/University | Institution | Result) rather than a
two-column page layout.

This is a DIFFERENT problem from pdf_parser._split_columns (which detects a
sidebar-vs-body PAGE layout). A table has several narrow columns, a bold
header row naming them, and cells that often wrap across multiple physical
lines at slightly different y-positions per column -- naive top-to-bottom
sorting scrambles it (confirmed against a real resume: "CGPA: 7.50" ends up
nowhere near "B.Tech CSE", and a wrapped "Institution" cell interleaves with
the next row entirely).

Real coordinates from a genuine test case (Pratik_Lad_Resume1.pdf):
    Examination  Board/University  Institution              Result
    B.Tech CSE   DYPATU            D. Y. Patil               CGPA: 7.50
    (Pursuing)                     Agriculture &
                                    Technical
                                    University, Talsande
    HSC          State Board       Shivraj Vidyalaya,         60%
                                    Murgud
    SSC          State Board       New English                76%
                                    Medium School,
                                    Murgud

Note the "Shivraj Vidyalaya," continuation line (y0=479.2) actually starts
BEFORE its row's other cells (y0=483.1) because the previous row's Institution
cell wrapped to 4 lines, pushing layout around slightly. A naive y-range
bucket would misassign it to the wrong row; nearest-anchor-by-distance gets
it right (479.2 is 3.9pt from the HSC row's anchor vs 90.6pt from B.Tech's).
"""
import re
from dataclasses import dataclass

from parsers.pdf_parser import Line

_BULLET_RE = re.compile(r"^[•\-\*\u2022]|^\d+[.)]")


@dataclass
class TableRow:
    cells: dict[str, str]

    def as_text(self, column_order: list[str]) -> str:
        parts = [f"{h}: {self.cells[h]}" for h in column_order if self.cells.get(h)]
        return " | ".join(parts)


def _find_header(lines: list[Line]) -> tuple[list[Line], int] | None:
    """A table header is >=3 bold lines sharing the same y0, left-to-right."""
    if not lines:
        return None
    y0 = lines[0].y0
    if not lines[0].bold:
        return None
    header = [lines[0]]
    i = 1
    while i < len(lines) and abs(lines[i].y0 - y0) < 1.0 and lines[i].bold:
        header.append(lines[i])
        i += 1
    if len(header) < 3:
        return None
    return sorted(header, key=lambda l: l.x0), i


def _column_bucket(x0: float, boundaries: list[float]) -> int:
    for i, b in enumerate(boundaries):
        if x0 < b:
            return i
    return len(boundaries)


def _split_column_into_rows(items: list[Line], typical_gap: float) -> list[str]:
    """Within ONE column's own lines (already y-sorted), a gap much bigger
    than the normal single-line-wrap spacing means a new row started, not a
    continuation of the same cell. This is evaluated per-column, in
    isolation -- comparing against another column's row positions is exactly
    what caused a long, 4-line-wrapped Institution cell to get misassigned to
    the NEXT row (its last wrapped line ends up geometrically closer to the
    next row's anchor than to its own row's anchor once a cell wraps that
    far). A column only ever needs to know about its OWN line spacing.
    """
    if not items:
        return []
    rows: list[list[str]] = [[items[0].text]]
    for prev, cur in zip(items, items[1:]):
        gap = cur.y0 - prev.y0
        if gap > typical_gap * 1.6:
            rows.append([cur.text])
        else:
            rows[-1].append(cur.text)
    return [" ".join(r) for r in rows]


def detect_and_reconstruct(lines: list[Line], typical_gap: float | None = None) -> list[str] | None:
    """If `lines` opens with a table header, return one reconstructed text
    line per table row (column-labelled, e.g. "Examination: B.Tech CSE
    (Pursuing) | Board/University: DYPATU | ..."). Returns None if no table
    header is found, so the caller falls back to normal paragraph handling.

    `typical_gap` is the expected vertical distance between two lines that
    are part of the SAME wrapped cell (roughly font-size * ~1.3-1.4). If not
    given, it's estimated from the header row's own font size.
    """
    found = _find_header(lines)
    if found is None:
        return None
    header, body_start = found
    column_order = [h.text.strip() for h in header]
    boundaries = [(header[i].x0 + header[i + 1].x0) / 2 for i in range(len(header) - 1)]

    body = lines[body_start:]
    if not body:
        return None
    if typical_gap is None:
        typical_gap = header[0].size * 1.4

    # bucket lines by column, each kept in y-order, then split each column
    # into rows independently using its own gaps
    by_col: dict[int, list[Line]] = {}
    for l in body:
        col = _column_bucket(l.x0, boundaries)
        by_col.setdefault(col, []).append(l)

    col_rows: dict[str, list[str]] = {}
    n_rows = 0
    for col_idx, items in by_col.items():
        items.sort(key=lambda l: l.y0)
        name = column_order[col_idx] if col_idx < len(column_order) else column_order[-1]
        col_rows[name] = _split_column_into_rows(items, typical_gap)
        n_rows = max(n_rows, len(col_rows[name]))

    out = []
    for i in range(n_rows):
        cells = {h: (col_rows.get(h, [])[i] if i < len(col_rows.get(h, [])) else "")
                for h in column_order}
        text = TableRow(cells).as_text(column_order)
        if text:
            out.append(text)
    return out or None
