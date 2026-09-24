"""JD Alignment Score.

Deliberately NOT called an ATS score. We have no ATS; real ATS platforms use
parsing rules and boolean filters we cannot observe. Calling this an ATS score
would be an indefensible claim, so we don't make it.
"""
import json
import math
import re
from functools import lru_cache

from config import settings
from matching import normalizer
from schemas import (Fact, GapItem, GapReport, Match, Requirement,
                     RequirementSet, ScoreCard)
from validation import entity_guard


@lru_cache(maxsize=1)
def _pair_calibration() -> dict:
    return json.loads((settings.resources / "pair_calibration.json").read_text(encoding="utf-8"))


def _pair_decision(total: float, resp: float, keyword: float,
                   matches: list[Match]) -> tuple[str, float]:
    """Calibrated evidence decision, independent of the display score bands.

    The binary calibration uses several independent signals instead of moving
    the old low-fit threshold until this dataset passes. A strict match band is
    separate because the reviewed set contains only one true match.
    """
    cal = _pair_calibration()
    values = {"score": total, "resp": resp, "covered": sum(m.status == "covered" for m in matches),
              "keyword": keyword}
    z = cal["intercept"] + sum(w * values[name] for name, w in zip(cal["features"], cal["coefficients"]))
    probability = 1.0 / (1.0 + math.exp(-max(-60.0, min(60.0, z))))
    if total >= cal["match_score_floor"]:
        return "match", probability
    return ("partial" if probability >= cal["probability_cutoff"] else "mismatch"), probability


def _weighted(matches: dict[str, Match], reqs: list[Requirement], types: set[str]) -> float:
    picked = [r for r in reqs if r.type in types]
    if not picked:
        return 0.0
    num = sum(r.weight * matches[r.req_id].score for r in picked)
    den = sum(r.weight for r in picked)
    return round(100.0 * num / den, 1) if den else 0.0


def _mean(matches: dict[str, Match], reqs: list[Requirement], types: set[str]) -> float:
    picked = [r for r in reqs if r.type in types]
    if not picked:
        return 0.0
    return round(100.0 * sum(matches[r.req_id].score for r in picked) / len(picked), 1)


def _qualification(matches: dict[str, Match], reqs: list[Requirement]) -> tuple[float, bool]:
    """Returns (score, applicable). When the JD states no qualification
    requirements, this component is NOT applicable and must not silently hand
    out its 20-point weight for free -- that alone was worth 20 points on a
    completely unrelated resume/JD pair, which is exactly the "scores 50 on a
    total mismatch" bug. `score()` renormalises weights over applicable
    components only.
    """
    quals = [r for r in reqs if r.type == "qualification"]
    if not quals:
        return 0.0, False
    # Preserve partial evidence as partial. The prior boolean cutoff promoted a
    # 0.40 semantic near-match to 100 qualification coverage.
    return round(100.0 * sum(matches[r.req_id].score for r in quals) / len(quals), 1), True


def _keyword_surface(jd_text: str, resume_text: str) -> float:
    # Reuse the same curated generic-English/resume vocabulary the validator
    # uses for UCR checks. The previous ~15-word stoplist let ordinary words
    # ("team", "process", "reporting", "analysis"...) count as "keyword
    # matches" against ANY resume regardless of domain, which was a real
    # contributor to unrelated resumes scoring ~50 against a senior AML role.
    vocab = entity_guard.generic_vocab()
    terms = {
        w for w in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.\-]{3,}", jd_text.lower())
        if w not in vocab
    }
    if not terms:
        return 0.0
    blob = resume_text.lower()
    hits = sum(1 for t in terms if t in blob)
    return round(100.0 * hits / len(terms), 1)


def score(req_set: RequirementSet, matches: list[Match], facts: list[Fact],
          resume_text: str) -> tuple[ScoreCard, GapReport]:
    by_id = {m.req_id: m for m in matches}
    reqs = req_set.requirements

    has_hard = any(r.type in {"hard_skill", "tool"} for r in reqs)
    has_resp = any(r.type == "responsibility" for r in reqs)
    hard = _weighted(by_id, reqs, {"hard_skill", "tool"})
    resp = _mean(by_id, reqs, {"responsibility"})
    qual, has_qual = _qualification(by_id, reqs)
    keyw = _keyword_surface(req_set.jd_text, resume_text)

    # Renormalise weights over components that actually apply to this JD.
    # A JD with no explicit qualification line must not hand out qualification's
    # 20-point weight for free -- redistribute it proportionally to the
    # components that DO have real requirements to check.
    parts = [(settings.w_hard, hard, has_hard), (settings.w_resp, resp, has_resp),
             (settings.w_qual, qual, has_qual), (settings.w_keyword, keyw, True)]
    applicable_weight = sum(w for w, _, ok in parts if ok) or 1.0
    total = round(sum((w / applicable_weight) * v for w, v, ok in parts if ok), 1)

    decision, probability = _pair_decision(total, resp, keyw, matches)
    card = ScoreCard(jd_alignment_score=total, hard_skill_coverage=hard,
                     responsibility_match=resp, qualification_match=qual,
                     keyword_surface=keyw, fit_decision=decision,
                     fit_probability=round(probability, 4))

    fact_text = {f.fact_id: f.text for f in facts}
    gap = GapReport()
    for r in reqs:
        m = by_id[r.req_id]
        ev = fact_text.get(m.fact_ids[0], "") if m.fact_ids else ""
        item = GapItem(req_id=r.req_id, requirement=r.text, must_have=r.must_have,
                       score=m.score, evidence=ev)
        if m.status == "missing":
            item.suggestion = ("Add this manually if you genuinely have it. "
                               "This system will not fabricate it.")
            (gap.missing_required if r.must_have else gap.missing_optional).append(item)
        elif m.status == "partial":
            item.suggestion = "Consider expanding this bullet if you did more than you wrote."
            gap.partial.append(item)

    return card, gap
