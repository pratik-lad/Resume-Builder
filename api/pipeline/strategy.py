"""Deterministic JD-driven optimization strategy over verified evidence only."""
from collections import defaultdict
import re

from matching import experience, normalizer, qualifications, scorer
from schemas import (ExperienceGap, Fact, Match, OptimizationAction, OptimizationStrategy,
                     ExperienceEntry, Requirement, RequirementCoverage, RequirementSet, ScoreCard)


def _importance(req: Requirement) -> str:
    if req.must_have and req.type in {"hard_skill", "tool", "qualification"}:
        return "critical"
    return "high" if req.must_have else "medium"


def coverage_analysis(reqs: list[Requirement], matches: list[Match],
                      facts: list[Fact], allow_unverified: bool = False) -> list[RequirementCoverage]:
    by_fact = {f.fact_id: f for f in facts}
    by_match = {m.req_id: m for m in matches}
    result: list[RequirementCoverage] = []
    for req in reqs:
        match = by_match.get(req.req_id, Match(req_id=req.req_id))
        evidence = [by_fact[fid].text for fid in match.fact_ids if fid in by_fact]
        status = match.status
        if allow_unverified and status == "missing":
            status = "covered"
            evidence = []
        if status == "covered":
            opportunity = "Keep this verified evidence prominent and use the JD's terminology only where equivalent."
            if allow_unverified and match.status == "missing":
                opportunity = "Surface this requirement prominently in the tailored resume."
        elif status == "partial":
            opportunity = ("Strengthen the cited existing evidence without adding scope, tools, metrics, or ownership."
                           if evidence else "Clarify this only if the candidate can supply source evidence.")
        else:
            opportunity = "Do not add this to the current resume; treat it as a gap or future project objective."
        confidence = (0.98 if match.method in {"lexical", "qualification:degree", "qualification:years",
                                               "qualification:degree+years", "qualification:certification",
                                               "qualification:experience_dates"}
                      else 0.85 if match.method == "fuzzy" else match.score if match.method == "semantic" else 0.0)
        if allow_unverified and match.status != "covered":
            confidence = 1.0
        result.append(RequirementCoverage(
            req_id=req.req_id, requirement=req.text, type=req.type, must_have=req.must_have,
            importance=_importance(req), status=status, confidence=round(confidence, 3),
            evidence_fact_ids=[fid for fid in match.fact_ids if fid in by_fact], evidence=evidence,
            improvement_opportunity=opportunity))
    return result


def build(req_set: RequirementSet, facts: list[Fact], matches: list[Match],
          card: ScoreCard, resume_text: str,
          experience_entries: list[ExperienceEntry] | None = None,
          allow_unverified: bool = False) -> OptimizationStrategy:
    coverage = coverage_analysis(req_set.requirements, matches, facts, allow_unverified=allow_unverified)
    by_req = {r.req_id: r for r in req_set.requirements}

    # Honest presentation ceiling: only partial requirements with cited evidence
    # are promoted in the hypothetical score. Missing requirements stay missing.
    potential_matches = [m.model_copy(update={"score": 1.0, "status": "covered"})
                         if m.status == "partial" and m.fact_ids else m for m in matches]
    potential, _ = scorer.score(req_set, potential_matches, facts, resume_text)
    potential_score = max(card.jd_alignment_score, potential.jd_alignment_score)

    # A project bridge can demonstrate technical requirements after real work is
    # completed and verified. It can never manufacture degree/certification or
    # professional-years evidence, so those requirements stay untouched here.
    project_matches = []
    for match in matches:
        req = by_req[match.req_id]
        bridgeable = (match.status == "missing" and req.must_have
                      and req.type in {"hard_skill", "tool", "responsibility"}
                      and req.min_years == 0)
        project_matches.append(match.model_copy(update={"score": 1.0, "status": "covered"})
                               if bridgeable else match)
    bridged, _ = scorer.score(req_set, project_matches, facts, resume_text)
    bridged_score = max(potential_score, bridged.jd_alignment_score)

    must = [c for c in coverage if c.must_have]
    must_coverage = (100 * sum(1 if c.status == "covered" else .5 if c.status == "partial" else 0
                               for c in must) / len(must)) if must else 100.0
    priority = {"critical": 3, "high": 2, "medium": 1}
    if allow_unverified:
        gaps = sorted((c for c in coverage if c.status != "covered"),
                      key=lambda c: (-priority[c.importance], c.status != "missing", c.req_id))
        coverage = [
            c.model_copy(update={"status": "covered",
                                "improvement_opportunity": "Surface this requirement prominently in the tailored resume."})
            if allow_unverified and c.status == "missing" else c
            for c in coverage
        ]
        gaps = sorted((c for c in coverage if c.status != "covered"),
                      key=lambda c: (-priority[c.importance], c.status != "missing", c.req_id))
    else:
        gaps = sorted((c for c in coverage if c.status != "covered"),
                      key=lambda c: (-priority[c.importance], c.status != "missing", c.req_id))

    relevance: dict[str, float] = defaultdict(float)
    req_ids_by_fact: dict[str, list[str]] = defaultdict(list)
    for match in matches:
        req = by_req[match.req_id]
        for fid in match.fact_ids:
            relevance[fid] = max(relevance[fid], req.weight * match.score)
            req_ids_by_fact[fid].append(req.req_id)

    # Rendering order should prefer literal JD terminology already visible in a
    # project/experience fact.  This deterministic signal is stronger than an
    # embedding near-match and makes relevant projects surface even when the
    # extractor omitted a technology from its structured `tech` field.
    for fact in facts:
        source = fact.text.lower()
        for req in req_set.requirements:
            hits = any(re.search(rf"(?<!\w){re.escape(surface)}(?!\w)", source, re.I)
                       for skill in req.canonical_skills
                       for surface in normalizer.expand(skill))
            if hits:
                relevance[fact.fact_id] = max(relevance[fact.fact_id], req.weight)
                if req.req_id not in req_ids_by_fact[fact.fact_id]:
                    req_ids_by_fact[fact.fact_id].append(req.req_id)
    stable = {f.fact_id: i for i, f in enumerate(facts)}
    fact_order = [f.fact_id for f in sorted(facts, key=lambda f: (-relevance[f.fact_id], stable[f.fact_id]))]

    actions: list[OptimizationAction] = []
    summaries = [f.fact_id for f in facts if f.type == "summary"]
    if summaries:
        actions.append(OptimizationAction(action="rewrite", target="summary", fact_ids=summaries,
            requirement_ids=[c.req_id for c in coverage if c.status != "missing"][:5],
            reason="Lead with the strongest source-supported capabilities relevant to this JD."))
    skills = [f.fact_id for f in facts if f.type == "skill"]
    if skills:
        actions.append(OptimizationAction(action="reorder", target="skills", fact_ids=skills,
            requirement_ids=[c.req_id for c in coverage if c.type in {"hard_skill", "tool"}],
            reason="Place verified JD-relevant skills first; never add missing JD skills."))
    for fact_type, target in (("experience_bullet", "experience"), ("project_bullet", "projects")):
        ids = [f.fact_id for f in facts if f.type == fact_type and req_ids_by_fact[f.fact_id]]
        if ids:
            actions.append(OptimizationAction(action="rewrite", target=target, fact_ids=ids,
                requirement_ids=list(dict.fromkeys(r for fid in ids for r in req_ids_by_fact[fid])),
                reason="Surface existing responsibilities and technologies that directly support JD requirements."))
            actions.append(OptimizationAction(action="reorder", target=target, fact_ids=ids,
                reason="Move the strongest verified evidence earlier in the section."))

    section_relevance = defaultdict(float)
    type_section = {"project_bullet": "projects", "experience_bullet": "experience"}
    for fact in facts:
        section_relevance[type_section.get(fact.type, fact.type)] += relevance[fact.fact_id]
    middle = ["projects", "experience"] if section_relevance["projects"] > section_relevance["experience"] else ["experience", "projects"]
    section_order = ["summary", "skills", *middle, "education", "certifications", "additional"]
    actions.append(OptimizationAction(action="reorder", target="sections",
        reason="Put sections with the strongest verified JD evidence first."))

    experience_gaps = []
    for req in req_set.requirements:
        if req.min_years <= 0:
            continue
        if experience_entries is not None:
            result, months, entry_ids = experience.qualification_result(req, experience_entries, req_set)
            candidate_years = round(months / 12, 2) if months is not None else None
            gap_years = round(max(0, req.min_years - candidate_years), 2) if candidate_years is not None else None
            source_supported = months is not None
        else:
            candidate_years = qualifications.self_declared_years(resume_text)
            gap_years = max(0, req.min_years - candidate_years) if candidate_years is not None else None
            source_supported = candidate_years is not None
            result = "satisfied" if gap_years == 0 else "unmet" if gap_years is not None else "unverifiable"
            months, entry_ids = None, []
        experience_gaps.append(ExperienceGap(
            req_id=req.req_id, requirement=req.text, required_years=req.min_years,
            candidate_years=candidate_years, gap_years=gap_years,
            source_supported=source_supported, qualification_result=result,
            verified_relevant_months=months, evidence_entry_ids=entry_ids,
        ))
        if result == "satisfied":
            actions.append(OptimizationAction(
                action="highlight", target="experience", requirement_ids=[req.req_id],
                reason="Surface the existing dated employment evidence; do not add or restate a years claim."))

    # Transferable evidence is a source fact with relevance to at least one
    # non-missing requirement. It is intentionally not a claim that a missing
    # requirement is possessed.
    transferable = [f for f in sorted(facts, key=lambda f: (-relevance[f.fact_id], stable[f.fact_id]))
                    if relevance[f.fact_id] > 0 and f.type in {"skill", "project_bullet", "experience_bullet"}]
    transferable_ids = [f.fact_id for f in transferable[:12]]
    transferable_skills = list(dict.fromkeys(
        f.text for f in transferable if f.type == "skill"
    ))[:12]
    keywords = list(dict.fromkeys(
        skill for c in coverage if c.status != "missing"
        for skill in by_req[c.req_id].canonical_skills
    ))[:15]

    limitations = []
    if potential_score < 90:
        limitations.append("Existing verified evidence cannot truthfully support a 90+ alignment score.")
    if any(c.status == "missing" and c.importance == "critical" for c in coverage):
        limitations.append("Critical missing requirements remain excluded from the optimized resume.")
    return OptimizationStrategy(
        current_score=card.jd_alignment_score,
        potential_score_existing_evidence=round(min(100.0, potential_score), 1),
        project_bridged_projected_alignment=round(min(100.0, bridged_score), 1),
        must_have_coverage=round(must_coverage, 1), coverage=coverage,
        prioritized_gap_ids=[c.req_id for c in gaps], actions=actions,
        section_order=section_order, fact_order=fact_order,
        transferable_evidence_fact_ids=transferable_ids,
        transferable_skills=transferable_skills,
        experience_gaps=experience_gaps, keyword_priorities=keywords,
        limitations=limitations)
