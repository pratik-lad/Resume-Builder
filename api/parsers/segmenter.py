"""Rule-based section segmentation. No LLM -- this must be fast, free and testable.

A line is a heading if it matches a known section name AND looks like a heading
(short, and either bold, larger than body text, or fully uppercase).
"""
import re
from dataclasses import dataclass, field

import yaml

from config import settings
from parsers.pdf_parser import Line, ParsedDoc
from parsers.tables import detect_and_reconstruct

_HEADINGS: dict[str, list[str]] = yaml.safe_load(
    (settings.resources / "section_headings.yaml").read_text(encoding="utf-8")
)
_LOOKUP = {v.lower(): canon for canon, variants in _HEADINGS.items() for v in variants}
_BULLET_RE = re.compile(r"^[•\-\*\u2022]|^\d+[.)]")


@dataclass
class Section:
    name: str
    lines: list[Line] = field(default_factory=list)

    @property
    def text(self) -> str:
        """Reconstruct flowing text from raw PDF lines.

        Two real bugs this fixes, both confirmed against an actual resume:

        1. Naively joining lines with '\\n' preserves the PDF's mid-sentence
           word-wraps. A section like a Summary paragraph gets fed to fact
           extraction with a literal newline in the middle of a sentence, and
           the LLM can split it into two "facts" right at that boundary,
           duplicating the wrapped words on both sides (observed in
           production: "...analytical problem-solving." / "analytical
           problem-solving. Hands-on..." -- the phrase repeats because the
           line-wrap boundary fell mid-sentence and got treated as two
           separate extraction units). Fixed by reflowing wrapped lines back
           into single paragraphs before extraction ever sees them.

        2. A genuine multi-column TABLE (e.g. Educational Qualification:
           Examination | Board | Institution | Result) is a completely
           different structure from a wrapped paragraph, and reading it
           top-to-bottom by y-position scrambles it -- "CGPA: 7.50" ends up
           nowhere near "B.Tech CSE". Detected and reconstructed row-by-row
           via parsers.tables before the reflow logic ever runs on it.
        """
        table_rows = detect_and_reconstruct(self.lines)
        if table_rows is not None:
            return "\n".join(table_rows)
        return "\n".join(_reflow(self.lines))

    @property
    def span(self) -> tuple[int, int]:
        if not self.lines:
            return (0, 0)
        return (self.lines[0].char_start, self.lines[-1].char_end)


def _reflow(lines: list[Line]) -> list[str]:
    """Merge PDF line-wraps back into flowing sentences/paragraphs.

    Heuristic: merge line[i] into line[i-1] with a space when line[i-1] does
    NOT end in terminal punctuation, line[i] does NOT start with a bullet/
    number marker, and the vertical gap between them matches normal
    single-line spacing (not a paragraph or bullet break).
    """
    if not lines:
        return []
    gaps = [lines[i + 1].y0 - lines[i].y0 for i in range(len(lines) - 1)]
    gaps = [g for g in gaps if g > 0]
    typical_gap = sorted(gaps)[len(gaps) // 2] if gaps else 14.0

    out: list[str] = [lines[0].text]
    for prev, cur in zip(lines, lines[1:]):
        gap = cur.y0 - prev.y0
        prev_ends_sentence = prev.text.rstrip().endswith((".", "!", "?", ":"))
        cur_is_bullet = bool(_BULLET_RE.match(cur.text.strip()))
        same_paragraph = (not prev_ends_sentence and not cur_is_bullet
                          and gap <= typical_gap * 1.4)
        if same_paragraph:
            out[-1] = f"{out[-1]} {cur.text}"
        else:
            out.append(cur.text)
    return out


def _normalise(text: str) -> str:
    t = re.sub(r"[^a-zA-Z& ]+", " ", text).strip().lower()
    return re.sub(r"\s+", " ", t)


def _short_enough(line: Line) -> bool:
    return len(line.text.split()) <= 5


def segment(doc: ParsedDoc) -> list[Section]:
    """
    A line becomes a new section heading when its ENTIRE normalised text exactly
    equals a known section name (e.g. "Education", "Skills") and it's short.

    We deliberately do NOT require bold/larger-font styling. Many plain resume
    templates render headings in the exact same size/weight as body text with
    no visual signal at all -- requiring styling there silently dropped whole
    sections into whichever section came before (Education bleeding into
    Summary, or into Skills). An exact whole-line match against a curated
    vocabulary is trustworthy on its own: a real sentence essentially never
    consists of nothing but a bare section name.
    """
    sections: list[Section] = []
    current = Section(name="header")

    for line in doc.lines:
        key = _normalise(line.text)
        canon = _LOOKUP.get(key)
        if canon and _short_enough(line):
            if current.lines:
                sections.append(current)
            current = Section(name=canon)
            continue
        current.lines.append(line)

    if current.lines:
        sections.append(current)

    # merge duplicates (resumes sometimes repeat a heading across pages)
    merged: dict[str, Section] = {}
    order: list[str] = []
    for s in sections:
        if s.name in merged:
            merged[s.name].lines.extend(s.lines)
        else:
            merged[s.name] = s
            order.append(s.name)
    return [merged[n] for n in order]


def summary(sections: list[Section]) -> dict[str, int]:
    return {s.name: len(s.lines) for s in sections}
