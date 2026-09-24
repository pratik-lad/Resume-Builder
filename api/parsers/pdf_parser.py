"""PyMuPDF extraction with column detection.

The single biggest parsing failure in real resumes: a naive page.get_text()
on a two-column layout interleaves the sidebar with the main body and produces
nonsense like "Skills Senior Engineer Python Acme Corp".

So we extract BLOCKS with bounding boxes, detect whether the page is two-column,
and read each column top-to-bottom before moving right.
"""
import re
from dataclasses import dataclass, field
from typing import Optional

import fitz  # PyMuPDF

from config import settings

# A bullet glyph is sometimes rendered in a different font (Wingdings/Symbol)
# than the text it introduces. PyMuPDF's line-grouping can then split the
# glyph into its own "line" entry positioned just AFTER its text line -- a
# ~0.5pt gap versus the normal ~14pt between real lines. Confirmed against a
# real resume: this produced literal orphaned "•" lines in the final output,
# one per bullet, disconnected from their content.
_BULLET_ONLY_RE = re.compile(r"^[•\-\*\u2022\u25CF\u25E6\u2023]+$")


@dataclass
class Line:
    text: str
    page: int
    x0: float
    y0: float
    size: float
    bold: bool
    char_start: int = 0
    char_end: int = 0

@dataclass
class ParsedDoc:
    lines: list[Line] = field(default_factory=list)
    raw_text: str = ""
    body_size: float = 10.0
    warnings: list[str] = field(default_factory=list)

    def is_degenerate(self) -> bool:
        """Scanned/image PDF -> trigger OCR fallback."""
        txt = self.raw_text
        if len(txt.strip()) < settings.ocr_min_chars:
            return True
        alnum = sum(c.isalnum() or c.isspace() for c in txt)
        return (alnum / max(len(txt), 1)) < settings.ocr_alnum_ratio


def _page_lines(page, pno: int) -> list[Line]:
    out: list[Line] = []
    blocks = [b for b in page.get_text("dict")["blocks"] if b.get("type") == 0]
    for b in blocks:
        for ln in b.get("lines", []):
            spans = ln.get("spans", [])
            if not spans:
                continue
            text = "".join(s["text"] for s in spans).strip()
            if not text:
                continue
            size = max(s["size"] for s in spans)
            bold = any("bold" in s.get("font", "").lower() for s in spans)
            out.append(Line(text=text, page=pno, x0=ln["bbox"][0], y0=ln["bbox"][1],
                            size=round(size, 1), bold=bold))
    return out


def _drop_orphan_bullet_glyphs(lines: list[Line]) -> list[Line]:
    """A line that is NOTHING but a bullet glyph, sitting within a couple of
    points of the previous line, carries no information -- the preceding
    line is already the bullet's content, and every downstream consumer
    (docx rendering, fact extraction) already treats one resume line as one
    bullet. Keeping it just produces a stray "•" as its own line/paragraph.
    """
    out: list[Line] = []
    for i, line in enumerate(lines):
        if _BULLET_ONLY_RE.match(line.text.strip()):
            if out and (line.y0 - out[-1].y0) < 3.0:
                continue  # glyph belongs to the line right above it -- drop
        out.append(line)
    return out


def _split_columns(lines: list[Line], page_height: float, page_width: float) -> list[Line]:
    """If the page is clearly two-column, read left fully, then right.

    A short table row (e.g. "B.Tech | XYZ College | 2020-2024 | CGPA 8.5" split
    across a few text spans) can superficially look like two clusters of x0
    values with a gap between them. That is NOT a two-column resume layout --
    it's one row. Real column layouts run for most of the page vertically;
    a table entry spans a few lines near one y-position. So beyond "enough
    lines on each side" and "a real gutter", we now also require BOTH sides to
    each cover a substantial vertical span of the page. A 3-4 line table
    can't satisfy that; a genuine sidebar/column can.
    """
    if len(lines) < 12:
        return sorted(lines, key=lambda l: l.y0)

    mid = page_width / 2.0
    left = [l for l in lines if l.x0 < mid * 0.92]
    right = [l for l in lines if l.x0 > mid * 1.02]

    if len(left) < 6 or len(right) < 6:
        return sorted(lines, key=lambda l: l.y0)

    gutter = min(l.x0 for l in right) - max(l.x0 for l in left)
    if gutter < page_width * settings.column_gap_ratio:
        return sorted(lines, key=lambda l: l.y0)

    # each "column" must span a real chunk of the page height, not one table row
    min_span = page_height * 0.25
    left_span = max(l.y0 for l in left) - min(l.y0 for l in left)
    right_span = max(l.y0 for l in right) - min(l.y0 for l in right)
    if left_span < min_span or right_span < min_span:
        return sorted(lines, key=lambda l: l.y0)

    return sorted(left, key=lambda l: l.y0) + sorted(right, key=lambda l: l.y0)


def parse_pdf(path: str) -> ParsedDoc:
    doc = fitz.open(path)
    all_lines: list[Line] = []
    warnings: list[str] = []

    for pno, page in enumerate(doc, start=1):
        lines = _page_lines(page, pno)
        # PyMuPDF's per-block line order is NOT reliable visual order -- a
        # bullet glyph in a different font can appear BEFORE its own text
        # line in the block's internal list despite having a numerically
        # larger y0 (confirmed against a real PDF). Establish true top-to-
        # bottom order first, THEN drop orphan glyphs, THEN hand off to
        # column detection (which does its own x-based re-sorting).
        lines = sorted(lines, key=lambda l: l.y0)
        lines = _drop_orphan_bullet_glyphs(lines)
        ordered = _split_columns(lines, page.rect.height, page.rect.width)
        all_lines.extend(ordered)

    # assign char spans against the reconstructed text
    cursor = 0
    chunks = []
    for ln in all_lines:
        ln.char_start = cursor
        ln.char_end = cursor + len(ln.text)
        cursor = ln.char_end + 1
        chunks.append(ln.text)

    raw = "\n".join(chunks)
    sizes = [l.size for l in all_lines] or [10.0]
    sizes.sort()
    body_size = sizes[len(sizes) // 2]

    parsed = ParsedDoc(lines=all_lines, raw_text=raw, body_size=body_size, warnings=warnings)
    if parsed.is_degenerate():
        parsed.warnings.append("PDF text looks degenerate (scanned?) - OCR fallback needed")
    return parsed
