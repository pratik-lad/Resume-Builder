"""Local, source-grounded human annotation surface for evaluation pairs.

Accepted annotations go to the evaluation CSV; drafts and rejection history
go to evaluation/review_states. External profiles and JDs are read-only.
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from threading import RLock
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from config import settings
from pipeline import jd as jd_stage, match as match_stage
from schemas import Fact, Requirement, RequirementSet
from review_annotations import prefill, requirement_atoms, skill_spans, explicit_skill_match


router = APIRouter(tags=["human review"])
CSV_NAME = "gold_label_review.csv"
PROPOSALS_NAME = "annotation_proposals.json"
PROPOSAL_STATUS_NAME = "annotation_proposals.status.json"
REVIEW_LOCK = RLock()
FACT_TYPES = {"experience_bullet", "project_bullet", "skill", "education", "certification", "summary", "other"}
REQ_TYPES = {"hard_skill", "tool", "responsibility", "qualification", "soft_skill"}
MATCH_METHODS = {"lexical", "fuzzy", "semantic", "none", "qualification:degree", "qualification:years", "qualification:degree+years", "qualification:certification"}
MATCH_STATUSES = {"covered", "partial", "missing"}


class RequirementDraft(BaseModel):
    req_id: str | None = None
    text: str
    type: Literal["hard_skill", "tool", "responsibility", "qualification", "soft_skill"]
    must_have: bool
    min_years: int = Field(ge=0)
    canonical_skills: list[str] = Field(default_factory=list)
    logic: Literal['single', 'any'] = 'single'
    source_text: str = ''


class MatchDraft(BaseModel):
    req_id: str | None = None
    score: float | None = Field(default=None, ge=0, le=1, allow_inf_nan=False)
    fact_keys: list[str] = Field(default_factory=list)
    status: Literal["covered", "partial", "missing"]
    method: Literal["lexical", "fuzzy", "semantic", "none", "qualification:degree", "qualification:years", "qualification:degree+years", "qualification:certification"]


class ReviewSave(BaseModel):
    fact_keys: list[str] = Field(default_factory=list)
    requirements: list[RequirementDraft] = Field(default_factory=list)
    matches: list[MatchDraft] = Field(default_factory=list)
    decision: Literal["match", "partial", "mismatch"] | None = None
    confidence: Literal["high", "medium", "low"] = "medium"
    notes: str = ""
    draft: bool = False
    reject_proposal: bool = False
    action: Literal['accept', 'draft', 'reject'] | None = None
    revision: str | None = None


def _state_path(row):
    # IDs are hashed so dataset contents cannot control filesystem paths.
    key = hashlib.sha256((row['resume_id']+'\n'+row['jd_id']).encode()).hexdigest()
    return settings.evaluation_dir / 'review_states' / (key+'.json')


def _state(row):
    path = _state_path(row)
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}


def _revision(row):
    return hashlib.sha256(_serialize({'row': row, 'state': _state(row)}).encode()).hexdigest()


def _save_state(row, value):
    path = _state_path(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json_atomic(path, value)


def _csv_path() -> Path:
    path = settings.evaluation_dir / CSV_NAME
    if not path.is_file():
        raise HTTPException(500, f"Review CSV not found: {path}")
    return path


def _proposal_path() -> Path:
    return settings.evaluation_dir / PROPOSALS_NAME


def _proposal_status_path() -> Path:
    return settings.evaluation_dir / PROPOSAL_STATUS_NAME


def _read_proposals() -> dict[str, Any]:
    path = _proposal_path()
    if not path.exists():
        return {"version": 1, "proposals": {}}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json_atomic(path: Path, payload: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _read_rows() -> tuple[list[dict[str, str]], list[str]]:
    with _csv_path().open(encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        return list(reader), list(reader.fieldnames or [])


def _sources() -> tuple[dict[int, dict[str, Any]], dict[str, dict[str, Any]]]:
    root = settings.evaluation_source_dir
    try:
        profiles = json.loads((root / "synthetic_profiles.json").read_text(encoding="utf-8"))
        jobs = json.loads((root / "scraped_jobs.json").read_text(encoding="utf-8"))
        benchmarks = json.loads((root / "benchmarks.json").read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise HTTPException(500, f"Review source data is unavailable: {exc.filename}") from exc
    job_map = {row["id"]: row for row in jobs}
    job_map.update({row["id"]: row for row in benchmarks.get("jobs", [])})
    return {int(row["profile_id"]): row for row in profiles}, job_map


def _pair(index: int) -> tuple[list[dict[str, str]], list[str], dict[str, str], dict[str, Any], dict[str, Any]]:
    rows, fields = _read_rows()
    if not 0 <= index < len(rows):
        raise HTTPException(404, "Review pair index not found")
    profiles, jobs = _sources()
    row = rows[index]
    profile = profiles.get(int(row["resume_id"]))
    job = jobs.get(row["jd_id"])
    if not profile or not job:
        raise HTTPException(500, "Selected review row no longer joins to its source profile or JD")
    return rows, fields, row, profile, job


def _fact_options(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """The complete set of permitted facts for a structured profile.

    The browser submits only these keys; the server creates every gold fact,
    preventing free-form facts or entities from entering the review CSV.
    """
    out: list[dict[str, Any]] = []
    def add(key: str, fact_type: str, parent_id: str, context: str, text: str, entities: dict[str, list[str]]) -> None:
        out.append({"key": key, "type": fact_type, "parent_id": parent_id, "context": context, "text": text, "entities": entities})
    for i, text in enumerate(profile.get("roles", []), 1):
        add(f"role:{i}", "experience_bullet", "roles", "roles", str(text), {"tech": [], "orgs": [], "numbers": [], "dates": []})
    for group in ("skills_primary", "skills_secondary"):
        for i, text in enumerate(profile.get(group, []), 1):
            add(f"{group}:{i}", "skill", group, group, str(text), {"tech": [str(text)], "orgs": [], "numbers": [], "dates": []})
    years = profile.get("experience_years")
    if isinstance(years, (int, float)):
        display = f"{years:g} years of experience"
        add("experience_years", "summary", "experience_years", "experience_years", display, {"tech": [], "orgs": [], "numbers": [str(years)], "dates": []})
    if profile.get("seniority"):
        add("seniority", "summary", "seniority", "seniority", str(profile["seniority"]), {"tech": [], "orgs": [], "numbers": [], "dates": []})
    for i, text in enumerate(profile.get("domains", []), 1):
        add(f"domain:{i}", "other", "domains", "domains", str(text), {"tech": [], "orgs": [], "numbers": [], "dates": []})
    for i, text in enumerate((profile.get("preferences") or {}).get("locations", []), 1):
        add(f"location:{i}", "other", "preferences.locations", "locations", str(text), {"tech": [], "orgs": [], "numbers": [], "dates": []})
    return out


def _stored_review(row: dict[str, str]) -> dict[str, Any]:
    def value(name: str, fallback: Any) -> Any:
        try:
            return json.loads(row.get(name) or "")
        except json.JSONDecodeError:
            return fallback
    facts = value("gold_facts", [])
    reqs = value("gold_requirements", [])
    matches = value("gold_matches", [])
    key_by_text = {fact.get("text"): fact.get("fact_id") for fact in facts if isinstance(fact, dict)}
    return {"facts": facts, "requirements": reqs, "matches": matches, "entities": value("gold_entities", {}),
            "decision": row.get("review_status", "").removeprefix("reviewed_") if row.get("review_status", "").startswith("reviewed_") else None,
            "confidence": row.get("confidence", "medium"), "notes": row.get("review_notes", ""), "fact_ids_by_text": key_by_text}


def _proposal_for(index: int) -> dict[str, Any] | None:
    return _read_proposals().get("proposals", {}).get(str(index))


def _decision_from_score(score: float) -> str:
    return "match" if score >= 75 else "partial" if score >= 50 else "mismatch"


def _generate_proposal(index: int, row: dict[str, str], profile: dict[str, Any], job: dict[str, Any], req_cache: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    options = _fact_options(profile)
    facts = [Fact(fact_id=f"F{i:02d}", type=item["type"], parent_id=item["parent_id"], context=item["context"], text=item["text"], entities=item["entities"]) for i, item in enumerate(options, 1)]
    job_id = str(job["id"])
    if job_id not in req_cache:
        extracted = jd_stage.extract(f"{job.get('title', '')}\n\n{job.get('description', '')}")
        source_text = f"{job.get('title', '')}\n{job.get('description', '')}".casefold()
        # A proposal must be traceable. Filter malformed/paraphrased LLM output
        # instead of silently promoting it to a review requirement.
        req_cache[job_id] = [item.model_dump() for item in extracted.requirements if item.text.casefold() in source_text]
    requirements = [Requirement(req_id=f"R{i:02d}", text=item["text"], type=item["type"], must_have=item["must_have"], min_years=item["min_years"], canonical_skills=item["canonical_skills"], weight=3.0 if item["must_have"] else 1.0) for i, item in enumerate(req_cache[job_id], 1)]
    req_set = RequirementSet(role_title=str(job.get("title", "")), requirements=requirements, jd_text=f"{job.get('title', '')}\n{job.get('description', '')}")
    matches, card, _ = match_stage.run(req_set, facts, "\n".join(f.text for f in facts)) if requirements else ([], None, None)
    fact_key_by_id = {f"F{i:02d}": option["key"] for i, option in enumerate(options, 1)}
    match_rows = [{"req_id": match.req_id, "score": match.score, "fact_keys": [fact_key_by_id[fact_id] for fact_id in match.fact_ids if fact_id in fact_key_by_id], "status": match.status, "method": match.method} for match in matches]
    evidence = {}
    try: evidence = json.loads(row.get("existing_label_evidence") or "{}")
    except json.JSONDecodeError: pass
    existing_decision = _decision_from_score(float(evidence["composite"])) if "composite" in evidence else None
    derived = card.fit_decision if card else "partial"
    # A documented human aggregate label is useful proposal evidence. Model
    # labels remain comparison evidence and do not override the local matcher.
    decision = existing_decision if row.get("existing_label_provenance") == "human_score_label" else derived
    uncertain_reasons = []
    if not requirements: uncertain_reasons.append("The LLM produced no exact JD requirements; add requirements manually.")
    if existing_decision and existing_decision != derived: uncertain_reasons.append("Existing aggregate label disagrees with source-grounded matcher proposal.")
    if card and (20 <= card.jd_alignment_score < 30 or 70 <= card.jd_alignment_score < 80): uncertain_reasons.append("Source-grounded score is close to a match-band boundary.")
    if row.get("existing_label_provenance", "").startswith("gemini"): uncertain_reasons.append("Existing label is model-generated and needs independent confirmation.")
    return {"status": "proposal", "provenance": {"facts_entities": "deterministic source-profile mapping", "requirements": "local LLM, exact-JD-phrase filtered", "matches": "local deterministic matcher", "existing_label": row.get("existing_label_provenance", "")}, "fact_keys": [item["key"] for item in options], "requirements": [{"text": r.text, "type": r.type, "must_have": r.must_have, "min_years": r.min_years, "canonical_skills": r.canonical_skills} for r in requirements], "matches": match_rows, "decision": decision, "confidence": "low" if uncertain_reasons else "medium", "uncertain": bool(uncertain_reasons), "uncertain_reasons": uncertain_reasons, "score_card": card.model_dump() if card else None}


def generate_all_proposals() -> dict[str, Any]:
    """Generate proposal-only annotations for the current 50-pair queue."""
    rows, _ = _read_rows(); profiles, jobs = _sources(); proposals: dict[str, Any] = {}; req_cache: dict[str, list[dict[str, Any]]] = {}
    _write_json_atomic(_proposal_status_path(), {"state": "running", "completed": 0, "total": len(rows)})
    for index, row in enumerate(rows):
        profile, job = profiles[int(row["resume_id"])], jobs[row["jd_id"]]
        proposals[str(index)] = _generate_proposal(index, row, profile, job, req_cache)
        _write_json_atomic(_proposal_status_path(), {"state": "running", "completed": index + 1, "total": len(rows)})
    payload = {"version": 1, "source_csv_sha256": hashlib.sha256(_csv_path().read_bytes()).hexdigest(), "proposals": proposals}
    _write_json_atomic(_proposal_path(), payload)
    _write_json_atomic(_proposal_status_path(), {"state": "complete", "completed": len(rows), "total": len(rows)})
    return {"total": len(rows), "uncertain": sum(item["uncertain"] for item in proposals.values())}


def reassess_existing_proposals() -> dict[str, Any]:
    """Refresh confidence flags without calling the LLM again."""
    payload = _read_proposals(); rows, _ = _read_rows()
    for index, row in enumerate(rows):
        proposal = payload["proposals"].get(str(index))
        if not proposal:
            continue
        evidence = {}
        try: evidence = json.loads(row.get("existing_label_evidence") or "{}")
        except json.JSONDecodeError: pass
        existing = _decision_from_score(float(evidence["composite"])) if "composite" in evidence else None
        score = float((proposal.get("score_card") or {}).get("jd_alignment_score", 50))
        derived = card.fit_decision if card else _decision_from_score(score)
        proposal["decision"] = existing if row.get("existing_label_provenance") == "human_score_label" else derived
        reasons = []
        if not proposal.get("requirements"): reasons.append("The LLM produced no exact JD requirements; add requirements manually.")
        if existing and existing != derived: reasons.append("Existing aggregate label disagrees with source-grounded matcher proposal.")
        if 20 <= score < 30 or 70 <= score < 80: reasons.append("Source-grounded score is close to a match-band boundary.")
        if row.get("existing_label_provenance", "").startswith("gemini"): reasons.append("Existing label is model-generated and needs independent confirmation.")
        proposal["uncertain_reasons"] = reasons; proposal["uncertain"] = bool(reasons); proposal["confidence"] = "low" if reasons else "medium"
    _write_json_atomic(_proposal_path(), payload)
    return {"total": len(payload["proposals"]), "uncertain": sum(item.get("uncertain", False) for item in payload["proposals"].values())}


def _serialize(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _validate_and_build(payload: ReviewSave, profile: dict[str, Any], job: dict[str, Any], complete: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    options = {item["key"]: item for item in _fact_options(profile)}
    if len(payload.fact_keys) != len(set(payload.fact_keys)) or any(key not in options for key in payload.fact_keys):
        raise HTTPException(422, "A selected fact is not a source-supported profile fact")
    facts, fact_id_by_key = [], {}
    for i, key in enumerate(payload.fact_keys, 1):
        item = options[key]
        fact_id = f"F{i:02d}"
        fact_id_by_key[key] = fact_id
        facts.append({"fact_id": fact_id, "type": item["type"], "parent_id": item["parent_id"], "context": item["context"], "text": item["text"], "entities": item["entities"], "source": {"page": 1, "char_start": 0, "char_end": 0}})
    requirements = []
    jd_text = f"{job.get('title', '')}\n{job.get('description', '')}".casefold()
    for i, item in enumerate(payload.requirements, 1):
        text = item.text.strip()
        if not text or text.casefold() not in jd_text:
            raise HTTPException(422, "Each requirement must be an exact phrase from the selected JD")
        canonical = [skill.strip() for skill in item.canonical_skills if skill.strip()]
        atoms = requirement_atoms(item.model_dump())
        if len(atoms)>1:
            raise HTTPException(422, f"Requirement {item.req_id or i} combines independent skills. Split into atomic requirements.")
        if atoms[0]['type'] != item.type:
            raise HTTPException(422, f"Requirement {item.req_id or i}: use type {atoms[0]['type']}.")
        if atoms[0].get('logic', 'single') != item.logic:
            raise HTTPException(422, f"Requirement {item.req_id or i}: preserve alternatives using 'any'.")
        if item.logic == 'any' and len(canonical)<2:
            raise HTTPException(422, 'Alternatives must contain at least two source skills')
        if item.source_text and (item.source_text.casefold() not in jd_text or text.casefold() not in item.source_text.casefold()):
            raise HTTPException(422, 'Requirement source context does not match the JD')
        if any(not skill_spans(text, [skill]) for skill in canonical):
            raise HTTPException(422, f"Requirement {item.req_id or i} contains a canonical skill absent from its source phrase")
        if item.must_have and not atoms[0]['must_have']:
            raise HTTPException(422, 'Preferred requirements must remain optional')
        req_id = item.req_id or f'R{i:02d}'
        if not re.fullmatch(r'R[0-9]+', req_id) or any(r['req_id']==req_id for r in requirements):
            raise HTTPException(422, 'Requirement IDs must be unique R01, R02, ...')
        requirements.append({"req_id": req_id, "text": text, "type": item.type, "must_have": item.must_have,
                             "min_years": item.min_years, "canonical_skills": canonical,
                             "logic": item.logic, "source_text": item.source_text,
                             "weight": 3.0 if item.must_have else 1.0})
    if len(payload.matches) != len(requirements):
        raise HTTPException(422, "Provide one evidence decision for each requirement")
    matches = []
    if any(m.req_id for m in payload.matches):
        by_id = {m.req_id: m for m in payload.matches}
        if len(by_id)!=len(payload.matches) or set(by_id)!={r['req_id'] for r in requirements}:
            raise HTTPException(422, 'Every match must reference one valid, unique requirement ID')
        ordered_matches = [by_id[r['req_id']] for r in requirements]
    else:
        ordered_matches = payload.matches
    for requirement, item in zip(requirements, ordered_matches):
        if len(item.fact_keys) != len(set(item.fact_keys)) or any(key not in fact_id_by_key for key in item.fact_keys):
            raise HTTPException(422, "A match cites a fact that was not selected")
        if item.status == "covered": score = 1.0
        elif item.status == "partial": score = 0.55
        else: score = 0.0
        if item.score is not None:
            score = item.score
        if ('covered' if score >= .75 else 'partial' if score >= .40 else 'missing') != item.status:
            raise HTTPException(422, 'Match score is inconsistent with its status')
        if item.status == "missing" and item.fact_keys:
            raise HTTPException(422, "A missing requirement cannot cite resume evidence")
        if item.status != "missing" and not item.fact_keys:
            raise HTTPException(422, "Covered or partial requirements must cite resume evidence")
        if item.status == "missing" and item.method != "none":
            raise HTTPException(422, "A missing requirement must use method 'none'")
        if item.status != 'missing' and item.method == 'none':
            raise HTTPException(422, 'Covered or partial matches need an evidence method')
        if requirement['logic']=='any' and item.status=='covered':
            cited = [options[k] for k in item.fact_keys]
            if explicit_skill_match(requirement, cited)['status']!='covered':
                raise HTTPException(422, 'Covered alternatives must cite at least one listed skill')
        matches.append({"req_id": requirement["req_id"], "fact_ids": [fact_id_by_key[key] for key in item.fact_keys],
                        "score": score, "method": item.method, "status": item.status})
    allowed = sorted({entity for fact in facts for group in fact["entities"].values() for entity in group}, key=str.casefold)
    entities = {"allowed_entities": allowed, "by_fact_id": {fact["fact_id"]: fact["entities"] for fact in facts}}
    if complete and (payload.decision is None or not facts or not requirements):
        raise HTTPException(422, "Complete review requires a decision, at least one fact, and at least one requirement")
    return facts, requirements, matches, entities


def _write_rows(rows: list[dict[str, str]], fields: list[str]) -> None:
    path = _csv_path()
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    os.replace(temporary, path)


@router.get("/v1/review/pairs")
def review_pairs() -> dict[str, Any]:
    rows, _ = _read_rows()
    proposals = _read_proposals().get("proposals", {})
    reviewed = sum(row.get("review_status", "").startswith("reviewed_") for row in rows)
    return {"total": len(rows), "reviewed": reviewed, "pairs": [
        {"index": i, "resume_id": row["resume_id"], "jd_id": row["jd_id"], "status": 'draft' if _state(row).get('draft') is not None else row.get("review_status"),
         "proposed_fit_label": row.get("proposed_fit_label"), "selection_group": row.get("selection_group"),
         "uncertain": bool(proposals.get(str(i), {}).get("uncertain"))}
        for i, row in enumerate(rows)
    ]}


@router.get("/v1/review/pairs/{index}")
def review_pair(index: int) -> dict[str, Any]:
    _, _, row, profile, job = _pair(index)
    options = _fact_options(profile)
    state = _state(row)
    proposal = _proposal_for(index)
    if state.get('draft') is not None:
        seed, origin = state['draft'], 'draft'
    elif row.get('review_status', '').startswith('reviewed_'):
        seed, origin = _stored_review(row), 'gold'
    else:
        seed, origin = proposal or _stored_review(row), 'proposal'
    seed = prefill(seed, options, normalize=origin=='proposal')
    errors = []
    try:
        _validate_and_build(ReviewSave.model_validate(seed), profile, job, True)
    except (HTTPException, ValueError) as exc:
        errors.append(str(exc.detail if isinstance(exc, HTTPException) else exc))
    return {"index": index, "row": row, "profile": profile, "job": job,
            "fact_options": options, "saved": _stored_review(row), "proposal": proposal,
            'seed': seed, 'origin': origin, 'validation_errors': errors,
            'revision': _revision(row), 'rejected': state.get('status')=='rejected'}


@router.get("/v1/review/proposals/status")
def proposal_status() -> dict[str, Any]:
    path = _proposal_status_path()
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"state": "not_generated", "completed": 0, "total": 0}


@router.put("/v1/review/pairs/{index}")
def save_review(index: int, payload: ReviewSave) -> dict[str, Any]:
    with REVIEW_LOCK:
        return _save_review(index, payload)


def _save_review(index: int, payload: ReviewSave) -> dict[str, Any]:
    rows, fields, row, profile, job = _pair(index)
    if payload.revision is not None and payload.revision != _revision(row):
        raise HTTPException(409, 'This pair changed in another tab. Reload before saving.')
    action = payload.action or ('reject' if payload.reject_proposal else 'draft' if payload.draft else None)
    if action is None:
        raise HTTPException(422, 'Explicit ACCEPT is required to write gold annotations')
    timestamp = datetime.now(timezone.utc).isoformat()
    if action == 'reject':
        _save_state(row, {'status': 'rejected', 'updated_at': timestamp, 'notes': payload.notes})
        if not row.get('review_status','').startswith('reviewed_'):
            row['review_status'] = 'proposal_rejected'
            _write_rows(rows, fields)
        return {"ok": True, "complete": False, "review_status": row["review_status"]}
    if action == 'draft':
        _save_state(row, {'status':'draft', 'updated_at':timestamp, 'draft':payload.model_dump(exclude={'action','revision','draft','reject_proposal'})})
        return {'ok':True, 'complete':False, 'review_status':'draft'}
    facts, requirements, matches, entities = _validate_and_build(payload, profile, job, True)
    row.update({"gold_facts": _serialize(facts), "gold_requirements": _serialize(requirements),
                "gold_matches": _serialize(matches), "gold_entities": _serialize(entities),
                "review_status": f"reviewed_{payload.decision}",
                "confidence": payload.confidence, "review_notes": payload.notes.strip()})
    _write_rows(rows, fields)
    _save_state(row, {'status':'accepted','updated_at':timestamp})
    return {"ok": True, "complete": True, "review_status": row["review_status"]}


@router.get("/review", response_class=HTMLResponse)
def review_page() -> str:
    return HTMLResponse((Path(__file__).parent / 'review_ui.html').read_text(encoding='utf-8'), headers={'Cache-Control':'no-store'})
