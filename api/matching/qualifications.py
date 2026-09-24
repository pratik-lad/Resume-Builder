"""Rule-based qualification matching -- degree level, years of experience,
and certifications -- kept SEPARATE from the generic lexical+semantic hybrid
used for skills.

Why this exists: a JD requirement like "Bachelor's Degree with 4+ years of
experience" was being scored by the SAME embedding-similarity matcher used
for skills. Semantic embeddings put "Bachelor's degree... 4+ years of AI/ML
experience" and "BTech Computer Science... pursuing" close together purely
because both are professional-qualification-shaped sentences -- regardless
of whether the degree matches, is complete, or the years are anywhere close.
Confirmed against a real case: an unrelated resume/JD pair scored 42.7
overall, propped up almost entirely by qualification-type requirements being
semantically "matched" against text that doesn't actually satisfy them.

The fix: for qualification-type requirements, don't guess by similarity --
check the specific, verifiable thing being asked for. If we can't verify it
(e.g. the resume never states a total-years figure), score it as NOT met.
An honest gap is always safer than a fabricated match -- the same principle
that governs the rest of this system's anti-hallucination design.
"""
import re
from functools import lru_cache

import yaml
from rapidfuzz import fuzz

from config import settings
from matching import experience
from schemas import ExperienceEntry, Fact, Requirement, RequirementSet

_YEARS_RE = re.compile(r"(\d+)\+?\s*(?:years|yrs)\b", re.IGNORECASE)


@lru_cache(maxsize=1)
def _degree_levels() -> dict[str, int]:
    raw = yaml.safe_load((settings.resources / "qualifications.yaml").read_text(encoding="utf-8"))
    return {k: int(v) for k, v in raw["degree_levels"].items()}


def _norm(text: str) -> str:
    return re.sub(r"[.\-]", "", text.lower())


def _degree_level_in(text: str) -> int | None:
    """Highest degree level mentioned in `text`, or None if it mentions none."""
    norm = _norm(text)
    best = None
    for kw, level in _degree_levels().items():
        if re.search(rf"\b{re.escape(kw)}\b", norm):
            best = level if best is None else max(best, level)
    return best


def _self_declared_years(resume_text: str) -> int | None:
    """Look for an explicit total-years statement ("4+ years of experience").
    We do NOT try to compute total years from date ranges -- that requires
    reliably parsing every experience date range including overlaps and
    "Present", which is its own unsolved problem. An explicit statement is
    the only thing we trust; anything else is a guess we're not willing to
    make on the resume's behalf.
    """
    matches = _YEARS_RE.findall(resume_text)
    return max((int(m) for m in matches), default=None)


def self_declared_years(resume_text: str) -> int | None:
    """Public, fail-closed accessor used to report (not infer) years gaps."""
    return _self_declared_years(resume_text)


def _certification_score(req_text: str, facts: list[Fact]) -> tuple[float, list[str]]:
    cert_texts = [f for f in facts if f.type == "certification"]
    pool = cert_texts or [f for f in facts if "certif" in f.text.lower()
                          or "licen" in f.text.lower()]
    if not pool:
        return 0.0, []
    best_fact, best_score = None, 0.0
    for f in pool:
        s = fuzz.partial_ratio(req_text.lower(), f.text.lower()) / 100.0
        if s > best_score:
            best_score, best_fact = s, f
    if best_score >= 0.55:  # partial_ratio on short cert names is naturally noisy
        return 1.0, [best_fact.fact_id]
    return 0.0, []


def try_match(req: Requirement, facts: list[Fact], resume_text: str,
             experience_entries: list[ExperienceEntry] | None = None,
             req_set: RequirementSet | None = None) -> tuple[float, str, list[str]] | None:
    """Returns (score, method, fact_ids) for a qualification-type requirement
    that matches a known rule (degree / years / certification), or None if
    the requirement doesn't fit any of those and should fall back to the
    generic hybrid matcher (e.g. "eligible to work in X region").
    """
    req_degree = _degree_level_in(req.text)
    req_years = req.min_years

    if req_degree is not None:
        edu_facts = [f for f in facts if f.type == "education"]
        resume_level = None
        for f in edu_facts:
            lvl = _degree_level_in(f.text)
            if lvl is not None:
                resume_level = lvl if resume_level is None else max(resume_level, lvl)
        degree_ok = resume_level is not None and resume_level >= req_degree
        fact_ids = [f.fact_id for f in edu_facts if _degree_level_in(f.text) is not None]

        if req_years > 0:
            if experience_entries is not None and req_set is not None:
                result, months, _ = experience.qualification_result(req, experience_entries, req_set)
                years_ok = result == "satisfied"
            else:
                years = _self_declared_years(resume_text)
                years_ok = years is not None and years >= req_years
            # both signals present: both must hold. An unmet or unverifiable
            # years requirement is not overridden by an unrelated degree match.
            return (1.0 if (degree_ok and years_ok) else 0.0,
                    "qualification:degree+years", fact_ids)
        return (1.0 if degree_ok else 0.0, "qualification:degree", fact_ids)

    if req_years > 0:
        if experience_entries is not None and req_set is not None:
            result, months, _ = experience.qualification_result(req, experience_entries, req_set)
            if result == "satisfied":
                score = 1.0
            elif result == "partial" and months is not None:
                score = min(0.999, months / (req_years * 12))
            else:
                score = 0.0
            return (score, "qualification:experience_dates", [])
        years = _self_declared_years(resume_text)
        years_ok = years is not None and years >= req_years
        # "Post-qualification experience" is narrower than total career years.
        # A generic "8 years of experience" fact cannot establish when those
        # years occurred relative to qualification, so fail closed unless the
        # resume explicitly makes the same claim.
        if re.search(r"post[\s\-\u2011\u2013]*qualification", req.text, re.I):
            years_ok = years_ok and bool(re.search(
                r"post[\s\-\u2011\u2013]*qualification", resume_text, re.I))
        return (1.0 if years_ok else 0.0, "qualification:years", [])

    if "certif" in req.text.lower() or "licen" in req.text.lower():
        score, fact_ids = _certification_score(req.text, facts)
        return (score, "qualification:certification", fact_ids)

    return None  # not a rule we recognise -- let the generic matcher handle it
