"""Stage 2: JD text -> typed, weighted requirements."""
import re
from config import settings
from llm import structured
from matching import normalizer
from pipeline.prompts import render
from review_annotations import requirement_atoms
from schemas import ExtractedRequirements, Requirement, RequirementSet


_EXPECTATION_HEADINGS = {
    "responsibilities", "responsibility", "requirements", "requirements and skills",
    "skills", "skills required", "required skills", "qualifications", "who can apply",
    "minimum qualifications", "preferred qualifications", "nice to have", "preferred skills",
}
_OPTIONAL_HEADINGS = {"preferred qualifications", "nice to have", "preferred skills"}


def _source_expectations(text: str) -> list[tuple[str, bool]]:
    """Recover every expectation line even when the local LLM omits rows."""
    active = False
    required = True
    candidates: list[tuple[str, bool]] = []
    for raw_line in text.splitlines():
        line = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", raw_line).strip()
        if not line:
            continue
        heading = line.rstrip(":").casefold()
        if heading in _EXPECTATION_HEADINGS:
            active = True
            required = heading not in _OPTIONAL_HEADINGS
            continue
        if re.match(r"^(?:about(?: the job| us)?|benefits?|equal opportunity|company)\s*:", line, re.I):
            active = False
            continue
        if not active:
            continue
        if re.match(r"^(?:we are looking for candidates|please do not apply)", line, re.I):
            continue
        optional = required and not bool(re.search(r"\b(?:extra credit|preferred|nice to have|bonus)\b", line, re.I))
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", line) if part.strip()]
        candidates.extend((part, optional) for part in parts if len(part.split()) >= 3)
    return candidates


def _inferred_requirement(text: str, must_have: bool) -> dict:
    skills = sorted(normalizer.technology_terms_in_text(text))
    years = re.search(r"(\d+)\s*\+?\s*years?", text, re.I)
    if years:
        kind = "qualification"
    elif re.search(r"\b(?:develop|design|build|test|deploy|write|maintain|architect|transform)\b", text, re.I):
        kind = "responsibility"
    elif skills:
        kind = "hard_skill"
    else:
        kind = "soft_skill"
    return {"text": text, "type": kind, "must_have": must_have,
            "min_years": int(years.group(1)) if years else 0,
            "canonical_skills": skills}


def _numeric_experience_requirements(jd_text: str) -> list[dict]:
    """Keep explicit numeric experience requirements even if the extractor omits them."""
    requirements = []
    pattern = re.compile(r"\b(\d+)\s*(?:\+|plus)?\s*(?:years?|yrs?)\b", re.I)
    for raw_line in jd_text.splitlines():
        line = re.sub(r"^\s*(?:[-*â€¢]|\d+[.)])\s*", "", raw_line).strip()
        match = pattern.search(line)
        if not match:
            continue
        requirements.append({
            "text": line,
            "type": "qualification",
            "must_have": not bool(re.search(r"\b(?:preferred|nice to have|bonus)\b", line, re.I)),
            "min_years": int(match.group(1)),
            "canonical_skills": sorted(normalizer.technology_terms_in_text(line)),
        })
    return requirements


def _title_from_jd(text: str) -> str:
    match = re.search(r"\b(?:as|for)\s+(?:an?\s+)?([A-Z][A-Za-z .+/-]{2,50}?(?:Developer|Engineer|Scientist|Analyst|Manager|Designer))\b",
                      text, re.I)
    return match.group(1).strip() if match else ""


def _chunks(text: str, size: int = 6000) -> list[str]:
    """Process the entire JD in bounded chunks, including its final section."""
    chunks = []
    remaining = text.strip()
    while len(remaining) > size:
        cut = remaining.rfind("\n", 0, size)
        if cut < size // 2:
            cut = remaining.rfind(" ", 0, size)
        if cut < 1:
            cut = size
        chunks.append(remaining[:cut])
        remaining = remaining[cut:].lstrip()
    if remaining:
        chunks.append(remaining)
    return chunks


def extract(jd_text: str) -> RequirementSet:
    out = ExtractedRequirements()
    for chunk in _chunks(jd_text):
        prompt = render("jd_extraction.jinja", jd_text=chunk)
        extracted = structured.generate(
            prompt, ExtractedRequirements,
            model=settings.model_extract, temperature=settings.temp_extract,
        )
        out.requirements.extend(extracted.requirements)
        if not out.role_title:
            out.role_title = extracted.role_title

    normalized: list[dict] = []
    for r in out.requirements:
        if not r.text.strip():
            continue
        normalized.extend(requirement_atoms({
            "text": r.text.strip(), "type": r.type, "must_have": r.must_have,
            "min_years": r.min_years,
            "canonical_skills": sorted(normalizer.canonical_set(r.skills)),
        }))

    existing = {re.sub(r"\W+", " ", item["text"]).strip().casefold() for item in normalized}
    for text, must_have in _source_expectations(jd_text):
        key = re.sub(r"\W+", " ", text).strip().casefold()
        # A source sentence already represented verbatim by the LLM needs no fallback row.
        if key in existing:
            continue
        item = _inferred_requirement(text, must_have)
        normalized.extend(requirement_atoms(item))
        existing.add(key)

    for item in _numeric_experience_requirements(jd_text):
        key = re.sub(r"\W+", " ", item["text"]).strip().casefold()
        if key not in existing:
            normalized.extend(requirement_atoms(item))
            existing.add(key)

    requirements: list[Requirement] = []
    for i, item in enumerate(normalized, start=1):
        requirements.append(Requirement(
            req_id=f"R{i:02d}", weight=(settings.weight_must_have if item["must_have"]
                                        else settings.weight_nice_to_have), **item))
    # The title is presentation and routing metadata.  If a constrained local
    # model omits it, the first concise JD line is a deterministic fallback;
    # requirements themselves still come only from extracted/normalised JD text.
    first_line = next((line.strip(" -:\t") for line in jd_text.splitlines() if line.strip()), "")
    detected_title = _title_from_jd(jd_text)
    model_title = out.role_title.strip()
    role_title = detected_title or (model_title if model_title.casefold() not in {"about", "about the job", "job"}
                                    else "") or (first_line if len(first_line) <= 100 else "")
    return RequirementSet(role_title=role_title, requirements=requirements,
                          jd_text=jd_text.strip())
