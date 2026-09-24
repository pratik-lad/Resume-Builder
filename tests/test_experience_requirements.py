"""Regression coverage for source-date professional experience handling."""
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from matching import experience, matcher  # noqa: E402
from pipeline import project_bridge, strategy  # noqa: E402
from schemas import (ExperienceEntry, Fact, Match, OptimizationStrategy, Requirement,
                     RequirementCoverage, RequirementSet, ScoreCard)  # noqa: E402


def _requirements(min_years=1):
    technical = Requirement(req_id="R01", text="Build FastAPI services", type="hard_skill",
                            must_have=True, canonical_skills=["fastapi"])
    years = Requirement(req_id="R02", text=f"{min_years}+ years of experience in the relevant field",
                        type="qualification", must_have=True, min_years=min_years)
    return RequirementSet(role_title="Backend Engineer", requirements=[technical, years])


def _entry(start="Jan 2024", end="Jan 2025", evidence="Backend Engineer - built FastAPI services"):
    return ExperienceEntry(entry_id="EXP-DATE-01", company="Acme", role_title="Backend Engineer",
                           start_date=start, end_date=end, source_evidence=evidence)


def test_extraction_preserves_explicit_employment_fields_and_source_evidence():
    entries = experience.extract_entries("Acme | Backend Engineer | Jan 2024 - Jan 2025\nBuilt FastAPI services")
    assert len(entries) == 1
    assert entries[0].company == "Acme"
    assert entries[0].role_title == "Backend Engineer"
    assert entries[0].start_date == "Jan 2024"
    assert entries[0].end_date == "Jan 2025"
    assert "Built FastAPI services" in entries[0].source_evidence


def test_undated_source_employment_is_preserved_for_editable_resume_dates():
    entries = experience.extract_entries("ABC Technologies | Software Developer\nBuilt internal APIs")
    assert len(entries) == 1
    assert entries[0].company == "ABC Technologies"
    assert entries[0].role_title == "Software Developer"
    assert entries[0].start_date == ""
    assert entries[0].end_date == ""


def test_twelve_verified_months_satisfy_year_requirement():
    result, months, ids = experience.qualification_result(_requirements().requirements[1], [_entry()], _requirements())
    assert (result, months, ids) == ("satisfied", 12, ["EXP-DATE-01"])


def test_eight_verified_months_are_partial_not_invented_as_a_year():
    rs = _requirements()
    result, months, _ = experience.qualification_result(rs.requirements[1], [_entry("Jan 2024", "Sep 2024")], rs)
    assert (result, months) == ("partial", 8)


def test_missing_dates_are_unverifiable():
    rs = _requirements()
    missing_dates = _entry("", "")
    result, months, ids = experience.qualification_result(rs.requirements[1], [missing_dates], rs)
    assert (result, months, ids) == ("unverifiable", None, [])


def test_overlapping_jobs_are_merged_not_double_counted():
    rs = _requirements(2)
    entries = [_entry("Jan 2024", "Jan 2025"),
               ExperienceEntry(entry_id="EXP-DATE-02", company="Beta", role_title="FastAPI Engineer",
                               start_date="Jun 2024", end_date="Jun 2025",
                               source_evidence="FastAPI Engineer maintained FastAPI services")]
    result, months, _ = experience.qualification_result(rs.requirements[1], entries, rs)
    assert result == "partial"
    assert months == 17


def test_current_role_uses_current_date_without_claiming_future_months():
    rs = _requirements()
    current = _entry("Jan 2026", "", "Backend Engineer built FastAPI services")
    current.current = True
    result, months, _ = experience.qualification_result(rs.requirements[1], [current], rs,
                                                         today=date(2026, 9, 22))
    assert (result, months) == ("partial", 8)


def test_project_duration_is_not_professional_experience():
    rs = _requirements()
    project_fact = Fact(fact_id="PRJ-01", type="project_bullet", text="Jan 2024 - Jan 2026: Built FastAPI project")
    match = matcher.match(rs.requirements, [project_fact], project_fact.text, [], rs)[1]
    assert match.status == "missing"
    assert match.method == "qualification:experience_dates"


def test_years_requirement_never_enters_project_bridge():
    years = Requirement(req_id="R20", text="1+ years of experience in the relevant field",
                        type="qualification", must_have=True, min_years=1)
    rs = RequirementSet(role_title="Backend Engineer", requirements=[years])
    plan = OptimizationStrategy(current_score=0, potential_score_existing_evidence=0,
                                must_have_coverage=0,
                                coverage=[RequirementCoverage(req_id="R20", requirement=years.text,
                                    type="qualification", must_have=True, importance="critical", status="missing")])
    assert project_bridge.recommend(rs, plan) is None


def test_strategy_reports_date_backed_result():
    rs = _requirements()
    facts = [Fact(fact_id="EXP-01", type="experience_bullet", text="Built FastAPI services")]
    matches = matcher.match(rs.requirements, facts, facts[0].text, [_entry()], rs)
    plan = strategy.build(rs, facts, matches, ScoreCard(), facts[0].text, [_entry()])
    gap = next(item for item in plan.experience_gaps if item.req_id == "R02")
    assert gap.qualification_result == "satisfied"
    assert gap.verified_relevant_months == 12
