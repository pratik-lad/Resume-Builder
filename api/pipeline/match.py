"""Stage 3: match + score. No LLM at all -- fast, free and unit-testable."""
from matching import matcher, scorer
from schemas import ExperienceEntry, Fact, GapReport, Match, RequirementSet, ScoreCard


def run(req_set: RequirementSet, facts: list[Fact], resume_text: str,
        experience_entries: list[ExperienceEntry] | None = None,
        *, allow_unverified: bool = False) -> tuple[list[Match], ScoreCard, GapReport]:
    matches = matcher.match(req_set.requirements, facts, resume_text, experience_entries, req_set)
    if allow_unverified:
        matches = [match.model_copy(update={"score": 1.0, "status": "covered", "method": "configured"})
                   if match.status != "covered" else match
                   for match in matches]
    card, gap = scorer.score(req_set, matches, facts, resume_text,
                             allow_unverified=allow_unverified)
    return matches, card, gap
