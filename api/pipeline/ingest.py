"""Stage 1: parse -> segment -> Fact Ledger.

One LLM call PER SECTION, not one giant call. Small flat schemas keep a 4B model
accurate and keep constrained decoding fast.
"""
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from llm import structured
from config import settings
from parsers import docx_parser, ocr_fallback, pdf_parser, segmenter
from pipeline.prompts import render
from matching.experience import extract_entries
from schemas import ExtractedFact, ExtractedFacts, Fact, FactLedger, SourceSpan
from validation import entity_guard

log = logging.getLogger(__name__)

_SECTION_FACT_TYPE = {
    "experience": "experience_bullet",
    "projects": "project_bullet",
    "skills": "skill",
    "education": "education",
    "certifications": "certification",
    "summary": "summary",
}
_SKIP = {"header", "contact", "boilerplate"}
_PREFIX = {
    "experience_bullet": "EXP", "project_bullet": "PRJ", "skill": "SKL",
    "education": "EDU", "certification": "CRT", "summary": "SUM", "other": "OTH",
}
_LEADING_BULLET = re.compile(r"^[\s•*\-]+")


def _source_claim_lines(section_text: str) -> list[str]:
    """Return lossless claim lines used when a model omits fact text."""
    claims = []
    for raw in section_text.splitlines():
        line = raw.strip()
        if not line or re.match(r"^#{1,6}\s+", line):
            continue
        if re.match(r"(?i)^(?:dates?|period|employment dates?|date of birth|dob)\s*:", line):
            continue
        claims.append(_LEADING_BULLET.sub("", line).strip())
    return [line for line in claims if line]


def _recover_fact_text(extracted: ExtractedFacts, section_text: str) -> ExtractedFacts:
    """Repair incomplete structured output without discarding valid entities."""
    source_lines = _source_claim_lines(section_text)
    if not source_lines:
        return extracted
    if not extracted.facts:
        return ExtractedFacts(facts=[ExtractedFact(text=line) for line in source_lines])
    if not any(not item.text.strip() for item in extracted.facts):
        return extracted
    facts = []
    source_index = 0
    for item in extracted.facts:
        if item.text.strip():
            facts.append(item)
            continue
        replacement = source_lines[min(source_index, len(source_lines) - 1)]
        source_index += 1
        facts.append(item.model_copy(update={"text": replacement}))
    existing = {re.sub(r"\W+", " ", item.text).strip().casefold() for item in facts if item.text.strip()}
    for line in source_lines:
        key = re.sub(r"\W+", " ", line).strip().casefold()
        if key and key not in existing:
            facts.append(ExtractedFact(text=line))
            existing.add(key)
    return ExtractedFacts(facts=facts)


def parse_file(path: str) -> pdf_parser.ParsedDoc:
    suffix = Path(path).suffix.lower()
    if suffix == ".pdf":
        doc = pdf_parser.parse_pdf(path)
        if doc.is_degenerate():
            log.info("degenerate PDF text -> OCR fallback")
            ocr = ocr_fallback.ocr_pdf(path)
            if len(ocr.raw_text) > len(doc.raw_text):
                return ocr
        return doc
    if suffix in (".docx", ".doc"):
        return docx_parser.parse_docx(path)
    raise ValueError(f"unsupported file type: {suffix}")


def build_ledger(doc: pdf_parser.ParsedDoc, *, allow_unverified: bool = False) -> tuple[FactLedger, dict[str, int]]:
    sections = segmenter.segment(doc)
    facts: list[Fact] = []
    entity_groups: list[list[str]] = []
    counters: dict[str, int] = {}

    candidates = [section for section in sections
                  if section.name not in _SKIP and section.text.strip()]

    line_positions = {line.char_start: index for index, line in enumerate(doc.lines)}

    def source_heading(section) -> str:
        first_index = line_positions.get(section.lines[0].char_start, 0)
        return doc.lines[first_index - 1].text.strip() if first_index else section.name

    def extract_section(section):
        ftype = _SECTION_FACT_TYPE.get(section.name, "other")
        # These display sections are source text, not semantic classification.
        # Keep their prose and punctuation lossless instead of round-tripping it
        # through an LLM that may omit a sentence or normalize Unicode dashes.
        if section.name == "summary":
            text = " ".join(line.strip() for line in section.text.splitlines() if line.strip())
            return section, ftype, ExtractedFacts(facts=[ExtractedFact(text=text)])
        if section.name == "certifications":
            items = [_LEADING_BULLET.sub("", line).strip()
                     for line in section.text.splitlines() if line.strip()]
            return section, ftype, ExtractedFacts(
                facts=[ExtractedFact(text=item) for item in items if item]
            )
        prompt = render("fact_extraction.jinja",
                        section_type=section.name, section_text=section.text)
        extracted = structured.generate(
            prompt, ExtractedFacts,
            model=settings.model_extract, temperature=settings.temp_extract,
            retries=0, num_predict=settings.max_extract_tokens,
        )
        return section, ftype, _recover_fact_text(extracted, section.text)

    # Independent sections can be extracted concurrently. executor.map keeps
    # source order deterministic while the local Ollama server serves two calls.
    with ThreadPoolExecutor(max_workers=settings.extraction_workers) as pool:
        extracted_sections = list(pool.map(extract_section, candidates))

    for section, ftype, extracted in extracted_sections:
        start, end = section.span
        for ef in extracted.facts:
            if not ef.text.strip():
                continue
            prefix = _PREFIX.get(ftype, "OTH")
            counters[prefix] = counters.get(prefix, 0) + 1
            entities = {"tech": ef.tech, "orgs": ef.orgs,
                        "numbers": ef.numbers, "dates": ef.dates}
            for group in entities.values():
                entity_groups.append(group)
            facts.append(Fact(
                fact_id=f"{prefix}-{counters[prefix]:02d}",
                type=ftype, parent_id=section.name,
                section_heading=source_heading(section), context=ef.context,
                text=ef.text.strip(), entities=entities,
                source=SourceSpan(page=section.lines[0].page, char_start=start, char_end=end),
            ))

    # Employment duration is a deterministic source-data field. It is derived
    # exclusively from the Experience section; project dates never enter it.
    # In unverified/fabrication mode we intentionally stop treating source
    # résumé evidence as a hard constraint and let downstream stages decide
    # whether to promote unsupported claims.
    if allow_unverified:
        experience_entries = []
        allowed = sorted({item for group in entity_groups for item in group})
    else:
        experience_entries = [entry for section in sections if section.name == "experience"
                              for entry in extract_entries(section.text)]
        allowed = entity_guard.build_allowed(doc.raw_text, entity_groups)
    ledger = FactLedger(facts=facts, experience_entries=experience_entries,
                        allowed_entities=sorted(allowed), raw_text=doc.raw_text)
    return ledger, segmenter.summary(sections)
