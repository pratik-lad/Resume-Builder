"""The most important test file in the repo.

These are deliberate hallucination attacks. Every one of them must be caught.
If this file passes, the core guarantee (UCR = 0.00) holds.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from validation import entity_guard, ladder, numeric_guard, verb_ladder  # noqa: E402

RESUME = """
Pratik Lad
Built a REST API in FastAPI serving 3 internal dashboards
Assisted the data team with cleaning survey responses in Python and pandas
Developed a Streamlit app for visualising sales trends
Education: BTech Computer Science and Engineering
Skills: Python, FastAPI, SQL, pandas, Git
"""

ENTITY_GROUPS = [
    ["fastapi", "rest api", "python", "pandas", "streamlit", "sql", "git"],
    ["3"],
]


@pytest.fixture(scope="module")
def allowed():
    return entity_guard.build_allowed(RESUME, ENTITY_GROUPS)


EVIDENCE = "Built a REST API in FastAPI serving 3 internal dashboards"


# ---------- L1: invented entities ----------

@pytest.mark.parametrize("attack", [
    "Built a REST API in FastAPI and Kubernetes serving 3 internal dashboards",
    "Built a REST API in FastAPI deployed on AWS serving 3 internal dashboards",
    "Built a REST API in FastAPI at Google serving 3 internal dashboards",
    "Built a Dockerised REST API in FastAPI serving 3 internal dashboards",
])
def test_invented_entity_is_caught(attack, allowed):
    violations = entity_guard.check(attack, allowed)
    assert violations, f"L1 missed an invented entity in: {attack}"
    assert violations[0].layer == "L1"


def test_faithful_rewrite_passes(allowed):
    ok = "Built and maintained REST APIs in Python and FastAPI powering 3 internal dashboards"
    assert entity_guard.check(ok, allowed) == []


def test_possessive_ascii_suffix_does_not_create_an_l1_fragment():
    allowed = entity_guard.build_allowed("developer project", [])
    assert entity_guard.check("developer's project", allowed) == []
    assert "s" not in entity_guard.tokens("developer's project")


def test_possessive_curly_suffix_does_not_create_an_l1_fragment():
    allowed = entity_guard.build_allowed("candidate skills", [])
    assert entity_guard.check("candidate’s skills", allowed) == []
    assert "s" not in entity_guard.tokens("candidate’s skills")


@pytest.mark.parametrize("language", ["C", "C++", "C#"])
def test_c_family_entities_remain_meaningful_and_supported(language):
    allowed = entity_guard.build_allowed(language, [[language]])
    assert entity_guard.check(language, allowed) == []
    assert language.lower() in entity_guard.tokens(language)


def test_genuinely_unsupported_technology_still_fails_l1():
    allowed = entity_guard.build_allowed("Python FastAPI", [["Python", "FastAPI"]])
    violations = entity_guard.check("Built Kubernetes services", allowed)
    assert violations and violations[0].layer == "L1"
    assert "kubernetes" in violations[0].detail


# ---------- L2: invented numbers ----------

@pytest.mark.parametrize("attack", [
    "Built a REST API in FastAPI serving 3 dashboards, improving latency by 40%",
    "Built a REST API in FastAPI serving 12 internal dashboards",
    "Built a REST API in FastAPI used by 500 users across 3 dashboards",
])
def test_invented_number_is_caught(attack):
    violations = numeric_guard.check(attack, EVIDENCE)
    assert violations, f"L2 missed an invented number in: {attack}"
    assert violations[0].layer == "L2"


def test_existing_number_passes():
    assert numeric_guard.check("Shipped 3 dashboards behind a FastAPI service", EVIDENCE) == []


# ---------- L5: seniority inflation ----------

@pytest.mark.parametrize("attack", [
    "Led the data team in cleaning survey responses in Python and pandas",
    "Managed survey data cleaning in Python and pandas",
    "Spearheaded data cleaning for the survey pipeline",
])
def test_seniority_inflation_is_caught(attack):
    src = "Assisted the data team with cleaning survey responses in Python and pandas"
    violations = verb_ladder.check(attack, src)
    assert violations, f"L5 missed an ownership upgrade in: {attack}"
    assert violations[0].layer == "L5"


def test_lateral_verb_is_allowed():
    src = "Developed a Streamlit app for visualising sales trends"
    assert verb_ladder.check("Built a Streamlit app for sales trend visualisation", src) == []


def test_downgrade_is_allowed():
    src = "Led the migration of the reporting pipeline"
    assert verb_ladder.check("Contributed to the reporting pipeline migration", src) == []


# ---------- the ladder as a whole ----------

def test_ladder_stops_at_first_failure(allowed):
    attack = "Led a Kubernetes migration improving throughput by 60%"
    violations = ladder.validate(attack, EVIDENCE, allowed)
    assert violations
    assert violations[0].layer == "L1"   # cheapest layer fires first


def test_ucr_is_zero_for_grounded_text(allowed):
    grounded = [
        "Built and maintained REST APIs in Python and FastAPI powering 3 internal dashboards",
        "Developed a Streamlit app for sales trend visualisation",
    ]
    assert ladder.unsupported_claim_rate(grounded, allowed) == 0.0


def test_ucr_is_nonzero_for_hallucinated_text(allowed):
    bad = ["Led a Kubernetes migration on AWS"]
    assert ladder.unsupported_claim_rate(bad, allowed) > 0.0


def test_ucr_uses_same_morphology_rules_as_l1(allowed):
    text = "Developed APIs in Python powering dashboards"
    assert entity_guard.check(text, allowed) == []
    assert ladder.unsupported_claim_rate([text], allowed) == 0.0
