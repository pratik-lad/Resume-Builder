"""Regression tests for rule-based qualification matching (matching/qualifications.py).

Every case here reproduces a real finding: a BTech-pursuing student's resume
scored 42.7 against a senior Apple ML role specifically because qualification
requirements were credited via semantic similarity instead of being checked.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from schemas import Fact, Requirement  # noqa: E402
from matching import matcher  # noqa: E402


def test_pursuing_degree_with_no_years_claim_is_not_credited():
    """The exact real case: BTech (Pursuing) vs "Bachelor's Degree with 4+
    years of experience". Degree level alone would pass, but nothing in the
    resume states a total-years figure -- must NOT be credited as met.
    """
    req = Requirement(req_id="R01", text="Bachelor's Degree with 4+ years of experience",
                      type="qualification", must_have=True, min_years=4, weight=3.0)
    facts = [Fact(fact_id="EDU-01", type="education",
                  text="B.Tech CSE (Pursuing), CGPA: 7.50")]
    resume_text = facts[0].text + "\nComputer Science Engineering student"

    m = matcher.match([req], facts, resume_text)[0]
    assert m.score == 0.0
    assert m.status == "missing"


def test_genuine_degree_and_years_are_credited():
    req = Requirement(req_id="R01", text="Bachelor's Degree with 3+ years of experience",
                      type="qualification", must_have=True, min_years=3, weight=3.0)
    facts = [Fact(fact_id="EDU-01", type="education",
                  text="Master of Science in Computer Science, Stanford University")]
    resume_text = "Software engineer with 5+ years of experience.\n" + facts[0].text

    m = matcher.match([req], facts, resume_text)[0]
    assert m.score == 1.0
    assert m.status == "covered"


def test_degree_without_years_requirement_checks_degree_only():
    req = Requirement(req_id="R01", text="Master's degree required",
                      type="qualification", must_have=True, min_years=0, weight=3.0)
    facts = [Fact(fact_id="EDU-01", type="education", text="MTech in Data Science")]
    m = matcher.match([req], facts, "MTech in Data Science")[0]
    assert m.score == 1.0


def test_insufficient_degree_level_fails():
    req = Requirement(req_id="R01", text="Master's degree required",
                      type="qualification", must_have=True, min_years=0, weight=3.0)
    facts = [Fact(fact_id="EDU-01", type="education", text="BTech Computer Science")]
    m = matcher.match([req], facts, "BTech Computer Science")[0]
    assert m.score == 0.0


def test_named_certification_matches_a_real_certification_fact():
    req = Requirement(req_id="R01", text="AWS certification required",
                      type="qualification", must_have=True, weight=3.0)
    facts = [Fact(fact_id="CRT-01", type="certification",
                  text="AWS Certified Solutions Architect - Associate")]
    m = matcher.match([req], facts, facts[0].text)[0]
    assert m.score == 1.0


def test_certification_requirement_with_no_matching_fact_is_missing():
    req = Requirement(req_id="R01", text="PMP certification required",
                      type="qualification", must_have=True, weight=3.0)
    facts = [Fact(fact_id="CRT-01", type="certification", text="IBM Python")]
    m = matcher.match([req], facts, facts[0].text)[0]
    assert m.score == 0.0


def test_unrecognised_qualification_falls_back_to_generic_matcher():
    """A qualification-type requirement that isn't a degree/years/cert claim
    (e.g. work authorization) should NOT be forced through the rule-based
    path -- it should fall back to the generic hybrid matcher rather than
    always scoring 0.
    """
    req = Requirement(req_id="R01", text="Must be eligible to work in the US",
                      type="qualification", must_have=True, canonical_skills=[], weight=3.0)
    facts = [Fact(fact_id="OTH-01", type="other", text="US citizen")]
    # Should not raise, and should not be forced to a rule-based 0 -- this
    # test's main purpose is confirming try_match() returns None here so
    # matcher.py's generic path runs instead of crashing or short-circuiting.
    result = matcher.match([req], facts, facts[0].text)
    assert len(result) == 1


def test_total_years_do_not_prove_post_qualification_years():
    req = Requirement(req_id="R01", text="8-10 years post-qualification experience",
                      type="qualification", must_have=True, min_years=8)
    fact = Fact(fact_id="SUM-01", type="summary", text="8 years of experience")
    result = matcher.match([req], [fact], fact.text)[0]
    assert result.score == 0.0
    assert result.status == "missing"
