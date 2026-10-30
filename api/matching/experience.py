"""Date-backed professional experience qualification checks.

Only explicit entries extracted from an ``experience`` section enter this
module.  Project dates are deliberately invisible here: a project can show a
skill, but it cannot establish professional employment duration.
"""
from __future__ import annotations

import calendar
import re
from datetime import date

from matching import normalizer
from schemas import ExperienceEntry, Requirement, RequirementSet


_MONTHS = {name.lower(): number for number, name in enumerate(calendar.month_abbr) if name}
_MONTHS.update({name.lower(): number for number, name in enumerate(calendar.month_name) if name})
_DATE = r"(?:" + "|".join(sorted(_MONTHS, key=len, reverse=True)) + r")\.?\s+\d{4}|\d{1,2}[/-]\d{4}|\d{4}"
_RANGE = re.compile(rf"(?P<start>{_DATE})\s*(?:-|–|—|to)\s*(?P<end>{_DATE}|present|current|now)", re.I)


_ROLE_WORD = re.compile(r"\b(?:engineer|developer|analyst|manager|designer|architect|consultant|intern|lead|administrator|specialist)\b", re.I)


def _month(value: str, *, today: date) -> tuple[int, int] | None:
    value = value.strip().lower().replace(".", "")
    if value in {"present", "current", "now"}:
        return today.year, today.month
    numeric = re.fullmatch(r"(\d{1,2})[/-](\d{4})", value)
    if numeric:
        month, year = map(int, numeric.groups())
        return (year, month) if 1 <= month <= 12 else None
    named = re.fullmatch(r"([a-z]+)\s+(\d{4})", value)
    if named and named.group(1) in _MONTHS:
        return int(named.group(2)), _MONTHS[named.group(1)]
    if re.fullmatch(r"\d{4}", value):
        return int(value), 1
    return None


def extract_entries(section_text: str) -> list[ExperienceEntry]:
    """Extract explicit date ranges plus their nearby source wording.

    This is intentionally conservative: no range means no employment entry.
    ``source_evidence`` is copied source text, not a generated interpretation.
    """
    lines = [line.strip() for line in section_text.splitlines() if line.strip()]
    text = "\n".join(lines)
    entries: list[ExperienceEntry] = []
    for index, match in enumerate(_RANGE.finditer(text), start=1):
        before = text[:match.start()].splitlines()
        after = [line for line in text[match.end():].splitlines() if line.strip()]
        heading = before[-1].strip() if before else ""
        next_line = after[0].strip() if after else ""
        evidence = " ".join(part for part in (heading, match.group(0), next_line) if part)
        # Split only an explicit pipe-delimited heading. Other formats are
        # ambiguous, so retain them as role context rather than guessing which
        # words are an employer name.
        parts = [part.strip() for part in heading.split("|") if part.strip()]
        company = parts[0] if len(parts) >= 2 else ""
        role_title = parts[-1] if len(parts) >= 2 else heading
        entries.append(ExperienceEntry(
            entry_id=f"EXP-DATE-{index:02d}", company=company, role_title=role_title,
            start_date=match.group("start"), end_date=match.group("end")
            if match.group("end").lower() not in {"present", "current", "now"} else "",
            current=match.group("end").lower() in {"present", "current", "now"},
            source_evidence=evidence,
        ))
    # A common resume layout places ``Role | #Confidential`` on one line and a
    # product/client description on the next. The anonymized employer is the
    # source company; the following line is context, not the job title.
    for index, line in enumerate(lines):
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if len(parts) < 2 or not _ROLE_WORD.search(parts[0]):
            continue
        if not re.fullmatch(r"#?\s*confidential\s*", parts[-1], re.I):
            continue
        role_title = parts[0]
        key = ("confidential", role_title.casefold())
        if key in {(entry.company.casefold(), entry.role_title.casefold()) for entry in entries}:
            continue
        context = lines[index + 1] if index + 1 < len(lines) else ""
        entries.append(ExperienceEntry(
            entry_id=f"EXP-UNDATED-{len(entries) + 1:02d}",
            company="#Confidential", role_title=role_title,
            source_evidence=" ".join(part for part in (line, context) if part),
        ))

    # Preserve clearly-labelled but undated source roles too. They cannot be
    # used for duration calculation, but they stop JD-only employers from
    # replacing a source employment heading during finalization.
    known = {(entry.company.casefold(), entry.role_title.casefold()) for entry in entries}
    for line in lines:
        heading = _RANGE.sub("", line).strip(" |-")
        parts = [part.strip() for part in heading.split("|") if part.strip()]
        if len(parts) < 2 or not _ROLE_WORD.search(heading):
            continue
        if re.fullmatch(r"#?\s*confidential\s*", parts[-1], re.I):
            continue
        company, role_title = parts[0], parts[-1]
        key = (company.casefold(), role_title.casefold())
        if key in known:
            continue
        entries.append(ExperienceEntry(
            entry_id=f"EXP-UNDATED-{len(entries) + 1:02d}", company=company,
            role_title=role_title, source_evidence=line,
        ))
        known.add(key)
    return entries


def _relevant(entry: ExperienceEntry, req_set: RequirementSet) -> bool:
    """Require literal JD technical terminology in the explicit job entry."""
    skills = {normalizer.canonical(skill) for req in req_set.requirements
              if req.type in {"hard_skill", "tool", "responsibility"}
              for skill in req.canonical_skills}
    if not skills:
        return False
    source = " ".join((entry.company, entry.role_title, entry.source_evidence)).lower()
    return any(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", source, re.I)
               for skill in skills for surface in normalizer.expand(skill))


def verified_relevant_months(entries: list[ExperienceEntry], req_set: RequirementSet,
                             *, today: date | None = None) -> tuple[int | None, list[str]]:
    """Return de-duplicated relevant months, or ``None`` when dates cannot verify it."""
    today = today or date.today()
    intervals: list[tuple[int, int, str]] = []
    saw_relevant = False
    for entry in entries:
        if not _relevant(entry, req_set):
            continue
        saw_relevant = True
        start = _month(entry.start_date, today=today)
        end = _month("current" if entry.current else entry.end_date, today=today)
        if not start or not end:
            continue
        start_index, end_index = start[0] * 12 + start[1], end[0] * 12 + end[1]
        if end_index > start_index:
            intervals.append((start_index, end_index, entry.entry_id))
    if not intervals:
        return None if not saw_relevant or any(_relevant(e, req_set) for e in entries) else 0, []
    intervals.sort()
    merged: list[list[int]] = []
    entry_ids: list[str] = []
    for start, end, entry_id in intervals:
        entry_ids.append(entry_id)
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return sum(end - start for start, end in merged), entry_ids


def qualification_result(req: Requirement, entries: list[ExperienceEntry], req_set: RequirementSet,
                         *, today: date | None = None) -> tuple[str, int | None, list[str]]:
    months, entry_ids = verified_relevant_months(entries, req_set, today=today)
    if months is None:
        return "unverifiable", None, []
    required = req.min_years * 12
    if months >= required:
        return "satisfied", months, entry_ids
    if months > 0:
        return "partial", months, entry_ids
    return "unmet", 0, []
