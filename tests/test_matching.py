import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from matching import matcher, normalizer  # noqa: E402
from schemas import Fact, Requirement  # noqa: E402


def test_alias_normalisation():
    assert normalizer.canonical("Postgres") == "postgresql"
    assert normalizer.canonical("PostgreSQL") == "postgresql"
    assert normalizer.canonical("sklearn") == "scikit-learn"
    assert normalizer.canonical("Node.js") == "nodejs"
    assert normalizer.canonical("RESTful APIs") == "rest api"


def test_unknown_term_survives_cleaned():
    assert normalizer.canonical("  Quantum Widgets ") == "quantum widgets"


def test_expand_round_trip():
    forms = normalizer.expand("postgresql")
    assert "postgres" in forms and "postgresql" in forms


def _skill(fid, text):
    return Fact(fact_id=fid, type="skill", text=text,
                entities={"tech": [text], "orgs": [], "numbers": [], "dates": []})


def test_alternatives_need_any_one_named_skill():
    req = Requirement(req_id="R1", text="AWS / Azure / GCP", type="tool",
                      must_have=True, canonical_skills=["aws", "azure", "gcp"], logic="any")
    result = matcher.match([req], [_skill("F1", "AWS")])[0]
    assert result.status == "covered"
    assert result.fact_ids == ["F1"]


def test_combined_skills_need_all_and_cite_exact_facts():
    req = Requirement(req_id="R1", text="Docker and Kubernetes", type="tool",
                      must_have=True, canonical_skills=["docker", "kubernetes"], logic="single")
    partial = matcher.match([req], [_skill("F1", "Docker")])[0]
    assert partial.status == "partial"
    assert partial.fact_ids == ["F1"]
    covered = matcher.match([req], [_skill("F1", "Docker"), _skill("F2", "Kubernetes")])[0]
    assert covered.status == "covered"
    assert covered.fact_ids == ["F1", "F2"]


def test_missing_named_skill_is_not_semantically_guessed(monkeypatch):
    req = Requirement(req_id="R1", text="Java", type="hard_skill", must_have=True,
                      canonical_skills=["java"])
    result = matcher.match([req], [_skill("F1", "Python")])[0]
    assert result.status == "missing"
    assert result.fact_ids == []
