"""Stage 3: match + score. No LLM at all -- fast, free and unit-testable."""
from matching import matcher, scorer
from schemas import ExperienceEntry, Fact, GapReport, Match, RequirementSet, ScoreCard


def run(req_set: RequirementSet, facts: list[Fact], resume_text: str,
        experience_entries: list[ExperienceEntry] | None = None) -> tuple[list[Match], ScoreCard, GapReport]:
    matches = matcher.match(req_set.requirements, facts, resume_text, experience_entries, req_set)
    card, gap = scorer.score(req_set, matches, facts, resume_text)
    return matches, card, gap
