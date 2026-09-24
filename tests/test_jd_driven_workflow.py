import sys
from pathlib import Path

from docx import Document
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from docgen import docx_builder  # noqa: E402
from pipeline import match as match_stage, optimize, project_bridge, strategy  # noqa: E402
from schemas import Fact, Match, Requirement, RequirementSet, RewriteOut  # noqa: E402
from validation import entity_guard  # noqa: E402


def skill(fid, text):
    return Fact(fact_id=fid, type="skill", parent_id="skills", context="skills", text=text,
                entities={"tech": [text], "orgs": [], "numbers": [], "dates": []})


def req(rid, text, skill_name, must=True):
    return Requirement(req_id=rid, text=text, type="hard_skill", must_have=must,
                       canonical_skills=[skill_name], weight=3 if must else 1)


def analyse(facts, requirements, title="AI Engineer"):
    rs = RequirementSet(role_title=title, jd_text="\n".join(r.text for r in requirements), requirements=requirements)
    matches, card, _ = match_stage.run(rs, facts, "\n".join(f.text for f in facts))
    plan = strategy.build(rs, facts, matches, card, "\n".join(f.text for f in facts))
    return rs, matches, card, plan


def test_same_domain_optimization_uses_existing_evidence():
    rs, matches, card, plan = analyse([skill("F1", "Python")], [req("R1", "Python", "python")])
    assert plan.coverage[0].status == "covered"
    assert plan.coverage[0].evidence_fact_ids == ["F1"]
    assert plan.must_have_coverage == 100
    assert project_bridge.recommend(rs, plan) is None


def test_cross_domain_gaps_and_transferable_evidence_are_separate():
    facts = [skill("F1", "Python"), skill("F2", "Docker")]
    requirements = [req("R1", "Python", "python"), req("R2", "PyTorch", "pytorch"), req("R3", "RAG", "rag")]
    rs, matches, card, plan = analyse(facts, requirements)
    states = {c.req_id: c.status for c in plan.coverage}
    assert states == {"R1": "covered", "R2": "missing", "R3": "missing"}
    bridge = project_bridge.recommend(rs, plan)
    assert bridge.status == "proposed"
    assert not bridge.eligible_as_resume_evidence
    assert {"pytorch", "rag"} <= set(bridge.technologies)
    assert plan.potential_score_existing_evidence < 90


def test_missing_requirement_never_gets_artificially_promoted():
    rs, matches, card, plan = analyse([skill("F1", "Python")],
                                      [req("R1", "Python", "python"), req("R2", "Kafka", "kafka")])
    assert next(c for c in plan.coverage if c.req_id == "R2").status == "missing"
    assert next(m for m in matches if m.req_id == "R2").fact_ids == []
    assert plan.potential_score_existing_evidence < 100


def test_project_bridge_is_not_rendered_into_current_resume(tmp_path):
    facts = [skill("F1", "Python")]
    rs, matches, card, plan = analyse(facts, [req("R1", "PyTorch", "pytorch")])
    bridge = project_bridge.recommend(rs, plan)
    path = docx_builder.build(facts, [], ["Candidate"], tmp_path / "resume.docx", plan)
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert bridge.title not in text
    assert "PyTorch" not in text
    assert "Python" in text


def test_ideal_project_claim_is_retained(monkeypatch):
    monkeypatch.setattr(optimize.ideal_resume, "generate",
                        lambda *args: "## Projects\nDeployed Kubernetes clusters for production")
    result = optimize.optimize([], [req("R1", "Kubernetes", "kubernetes")], [], set())
    assert "Kubernetes" in result.markdown
    assert result.reverted == 0 and result.ucr is None

def test_ideal_generation_retains_model_document(monkeypatch):
    markdown = "## Projects\nBuilt Python and FastAPI REST APIs"
    monkeypatch.setattr(optimize.ideal_resume, "generate", lambda *args: markdown)
    result = optimize.optimize([skill("F1", "Python")], [req("R1", "FastAPI", "fastapi")], [], set())
    assert "Built Python and FastAPI REST APIs" in result.markdown
    assert "## Selected Projects" in result.markdown
    assert result.truth_report is None

def test_project_status_requires_verification_before_evidence():
    rs, matches, card, plan = analyse([skill("F1", "Python")], [req("R1", "Kafka", "kafka")])
    project = project_bridge.recommend(rs, plan)
    assert not project_bridge.with_status(project, "completed", []).eligible_as_resume_evidence
    with pytest.raises(ValueError):
        project_bridge.with_status(project, "verified", [])
    verified = project_bridge.with_status(project, "verified", ["repository review", "passing tests"])
    assert verified.eligible_as_resume_evidence


def test_build_project_mode_remains_explicitly_proposed():
    rs, matches, card, plan = analyse([skill("F1", "Python")], [req("R1", "Kafka", "kafka")])
    build = project_bridge.build_plan(project_bridge.recommend(rs, plan))
    assert build.status == "proposed"
    assert "NOT YET COMPLETED" in build.resume_evidence_warning
    assert "Dockerfile" in build.files


def test_project_bridge_excludes_professional_years_requirement():
    facts = [skill("F1", "Python")]
    requirements = [
        req("R1", "Kafka", "kafka"),
        Requirement(req_id="R2", text="1+ years of professional experience",
                    type="qualification", must_have=True, min_years=1, weight=3),
    ]
    rs, _, _, plan = analyse(facts, requirements)
    bridge = project_bridge.recommend(rs, plan)
    assert "Kafka" in bridge.requirements_covered
    assert all("years" not in item.lower() for item in bridge.requirements_covered)
