"""Validation for candidate identity and other facts the optimizer may never edit.

This is deliberately separate from the claim validator.  An immutable value can
be source-supported and still be wrong if it was changed (for example, a real
college name replacing the candidate's college).  We therefore protect exact
source anchors before and after rendering.
"""
from __future__ import annotations

import re
from pathlib import Path

from docx import Document

from schemas import Fact, Rewrite

_SPACE = re.compile(r"\s+")
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
_PHONE = re.compile(r"(?:\+?\d[\d .()\-]{7,}\d)")
_URL = re.compile(r"(?:https?://|www\.|linkedin\.com/|github\.com/)[^\s|,;]+", re.I)


def _normalise(value: str) -> str:
    return _SPACE.sub(" ", value or "").strip().casefold()


def contact_values(raw_text: str) -> list[str]:
    """Return literal contact values from the source, without interpreting them."""
    head = "\n".join(raw_text.splitlines()[:15])
    values = _EMAIL.findall(head) + _PHONE.findall(head) + _URL.findall(head)
    return list(dict.fromkeys(v.strip() for v in values if v.strip()))


def immutable_anchors(facts: list[Fact], raw_text: str) -> list[str]:
    """Source values that must survive the generated resume exactly in substance."""
    lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
    anchors = [lines[0]] if lines else []  # candidate name/header as extracted from source
    anchors.extend(contact_values(raw_text))
    for fact in facts:
        # Education and certification content is immutable. Context carries the
        # college/issuer where the extractor stored it.
        if fact.type in {"education", "certification"}:
            anchors.extend([fact.text, fact.context])
        # Context labels for work/project bullets carry employer, job title and
        # dates. The bullet itself is safely rewritable; its metadata is not.
        if fact.type == "experience_bullet" and fact.context:
            anchors.append(fact.context)
    return list(dict.fromkeys(a for a in anchors if len(_normalise(a)) >= 2))


def validate_rewrites(facts: list[Fact], rewrites: list[Rewrite]) -> list[str]:
    """Reject any attempt to rewrite education, certification, or role metadata."""
    by_id = {fact.fact_id: fact for fact in facts}
    errors: list[str] = []
    for rewrite in rewrites:
        fact = by_id.get(rewrite.fact_id)
        if not fact:
            errors.append(f"rewrite references unknown fact {rewrite.fact_id}")
        elif fact.type in {"education", "certification"}:
            errors.append(f"immutable {fact.type} fact {fact.fact_id} was targeted for rewrite")
    return errors


def validate_document(path: Path, facts: list[Fact], raw_text: str) -> list[str]:
    """Ensure immutable source anchors occur in the rendered DOCX body."""
    output = _normalise("\n".join(p.text for p in Document(path).paragraphs))
    missing = [anchor for anchor in immutable_anchors(facts, raw_text)
               if _normalise(anchor) not in output]
    return [f"immutable source value missing from rendered DOCX: {value}" for value in missing]
