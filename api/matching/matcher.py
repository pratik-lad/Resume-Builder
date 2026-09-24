"""Hybrid matching: alias-normalised lexical OR calibrated semantic, whichever is higher.

They fail differently -- lexical is precise but brittle on paraphrase, semantic is
recall-friendly but mushy on exact technical tokens -- so taking the max is a real win.
"""
from rapidfuzz import fuzz

from config import settings
from matching import embedder, normalizer, qualifications
from schemas import ExperienceEntry, Fact, Match, Requirement, RequirementSet


def _calibrate(cos: float) -> float:
    """Raw BGE cosine sits in ~[0.45, 0.85]. Uncalibrated, every JD scores ~70."""
    lo, hi = settings.sem_cal_min, settings.sem_cal_max
    return max(0.0, min(1.0, (cos - lo) / (hi - lo)))


def _status(score: float) -> str:
    if score >= settings.covered_threshold:
        return "covered"
    if score >= settings.partial_threshold:
        return "partial"
    return "missing"


def match(requirements: list[Requirement], facts: list[Fact], resume_text: str = "",
          experience_entries: list[ExperienceEntry] | None = None,
          req_set: RequirementSet | None = None) -> list[Match]:
    if not requirements:
        return [Match(req_id=r.req_id) for r in requirements]

    # --- resume-side lexical index ---
    resume_canon: set[str] = set()
    fact_canon: list[set[str]] = []
    for f in facts:
        own: set[str] = set()
        for group in f.entities.values():
            own |= normalizer.canonical_set(group)
        if f.type == "skill":
            for part in f.text.replace("|", ",").split(","):
                if part.strip():
                    own.add(normalizer.canonical(part))
        fact_canon.append(own)
        resume_canon |= own
    resume_blob = " ".join(sorted(resume_canon))

    # --- semantic side ---
    sim = None
    if embedder.available():
        req_vecs = embedder.encode([r.text for r in requirements])
        fact_vecs = embedder.encode([f"{f.context} {f.text}".strip() for f in facts])
        if req_vecs is not None and fact_vecs is not None:
            sim = embedder.similarity_matrix(req_vecs, fact_vecs)

    results: list[Match] = []
    for i, req in enumerate(requirements):
        lex, lex_method = 0.0, "none"
        exact_skills: list[str] = []
        fuzzy_skills: list[str] = []
        lexical_fact_ids: list[str] = []
        wanted = [normalizer.canonical(s) for s in req.canonical_skills]
        for skill in wanted:
            c = normalizer.canonical(skill)
            if c in resume_canon:
                exact_skills.append(c)
                lexical_fact_ids.extend(facts[j].fact_id for j, own in enumerate(fact_canon) if c in own)
            elif fuzz.token_set_ratio(c, resume_blob) / 100.0 >= settings.fuzzy_threshold:
                fuzzy_skills.append(c)

        # Named technical requirements are evidence checks, not semantic guesses.
        # An OR group needs one alternative; a conjunction/single group needs all
        # named skills. Partial conjunction evidence stays partial. Responsibilities
        # may use a named technology as supporting evidence, but naming the tool does
        # not prove that the candidate performed the requested action.
        if wanted:
            hits = len(set(exact_skills + fuzzy_skills))
            complete = hits >= 1 if req.logic == "any" else hits == len(set(wanted))
            if complete:
                lex = 1.0 if exact_skills else 0.85
            elif hits:
                lex = 0.55
            lex_method = "lexical" if exact_skills else "fuzzy" if fuzzy_skills else "none"
            if req.type not in {"hard_skill", "tool"}:
                lex = min(lex, 0.55)

        sem, best_idx = 0.0, None
        if sim is not None:
            row = sim[i]
            best_idx = int(row.argmax())
            sem = _calibrate(float(row[best_idx]))

        # For an explicit hard skill/tool, absence of lexical evidence is a real
        # gap. Embeddings must not turn Java into Python or one cloud into another.
        if req.type in {"hard_skill", "tool"} and wanted:
            sem = 0.0

        if lex >= sem:
            score, method = lex, lex_method
            fact_ids = list(dict.fromkeys(lexical_fact_ids)) if score > 0 else []
        else:
            score, method = sem, "semantic"
            fact_ids = [facts[best_idx].fact_id] if (best_idx is not None and score > 0) else []

        # Qualification requirements (degree / years / certification) are
        # rule-checked, not similarity-guessed -- see matching/qualifications.py
        # for why. Only override when a rule actually recognises the
        # requirement shape; otherwise the generic hybrid score above stands
        # (e.g. "eligible to work in the US" isn't a degree/years/cert claim).
        if req.type == "qualification":
            override = qualifications.try_match(req, facts, resume_text,
                                                experience_entries, req_set)
            if override is not None:
                score, method, fact_ids = override
                results.append(Match(req_id=req.req_id, fact_ids=fact_ids,
                                     score=round(score, 3), method=method,
                                     status=_status(score)))
                continue

        results.append(
            Match(req_id=req.req_id, fact_ids=fact_ids, score=round(score, 3),
                  method=method, status=_status(score))
        )
    return results
