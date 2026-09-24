import sys
from pathlib import Path

from docx import Document

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from docgen import docx_builder  # noqa: E402
from pipeline import match as match_stage, optimize, project_bridge, strategy  # noqa: E402
from schemas import Fact, Match, Requirement, RequirementSet, Rewrite, RewriteOut  # noqa: E402
from validation import entity_guard, immutable_guard  # noqa: E402


def fact(fid, kind, text, context=""):
    return Fact(fact_id=fid, type=kind, parent_id=kind, context=context, text=text,
                entities={"tech": [], "orgs": [], "numbers": [], "dates": []})


def requirement(rid, text, skill, *, kind="hard_skill", years=0, required=True):
    return Requirement(req_id=rid, text=text, type=kind, must_have=required,
                       min_years=years, canonical_skills=[skill], weight=3 if required else 1)


def plan_for(facts, reqs, raw=None):
    raw = raw or "\n".join(item.text for item in facts)
    req_set = RequirementSet(role_title="GenAI Engineer", jd_text="\n".join(r.text for r in reqs), requirements=reqs)
    matches, score, _ = match_stage.run(req_set, facts, raw)
    return req_set, matches, strategy.build(req_set, facts, matches, score, raw)


def test_ideal_generation_uses_all_background(monkeypatch):
    facts = [fact("S1", "summary", "Backend developer"), fact("K1", "skill", "Python")]
    reqs = [requirement("R1", "Kubernetes", "kubernetes")]
    calls = []
    monkeypatch.setattr(optimize.ideal_resume, "generate",
                        lambda jd, background: (calls.append((jd, background)) or "## Skills\nKubernetes"))
    result = optimize.optimize(facts, reqs, [], set())
    assert "Backend developer" in calls[0][1] and "Python" in calls[0][1]
    assert "Kubernetes" in calls[0][0] and "Kubernetes" in result.markdown

def test_skills_and_projects_are_reordered_by_jd_evidence(tmp_path):
    facts = [
        fact("K1", "skill", "Java"), fact("K2", "skill", "Python"),
        fact("P1", "project_bullet", "Built a Java CLI utility", "Java Utility"),
        fact("P2", "project_bullet", "Built Python FastAPI REST APIs", "API Platform"),
    ]
    reqs = [requirement("R1", "Python", "python"), requirement("R2", "FastAPI", "fastapi")]
    _, _, plan = plan_for(facts, reqs)
    path = docx_builder.build(facts, [], ["Candidate"], tmp_path / "ordered.docx", plan)
    output = "\n".join(p.text for p in Document(path).paragraphs)
    assert output.index("Python") < output.index("Java")
    assert output.index("API Platform") < output.index("Java Utility")


def test_ideal_project_can_add_missing_skill(monkeypatch):
    facts = [fact("P1", "project_bullet", "Built Python APIs")]
    reqs = [requirement("R1", "Kubernetes", "kubernetes")]
    monkeypatch.setattr(optimize.ideal_resume, "generate",
                        lambda *args: "## Projects\nBuilt production Kubernetes APIs")
    result = optimize.optimize(facts, reqs, [], {"Python"})
    assert "Kubernetes" in result.markdown
    assert result.reverted == 0 and result.ucr is None

def test_experience_gap_is_reported_without_changing_candidate_years():
    facts = [fact("S1", "summary", "Backend engineer with 1 years of experience"), fact("K1", "skill", "Python")]
    reqs = [requirement("R1", "6 years of Python experience", "python", kind="qualification", years=6)]
    _, _, plan = plan_for(facts, reqs)
    gap = plan.experience_gaps[0]
    assert (gap.required_years, gap.candidate_years, gap.gap_years) == (6, 1, 5)
    assert plan.project_bridged_projected_alignment <= 100


def test_project_bridge_has_build_testing_deployment_and_remains_proposed():
    facts = [fact("K1", "skill", "Python")]
    reqs = [requirement("R1", "PyTorch", "pytorch"), requirement("R2", "RAG", "rag")]
    req_set, _, plan = plan_for(facts, reqs)
    bridge = project_bridge.recommend(req_set, plan)
    assert bridge.status == "proposed" and not bridge.eligible_as_resume_evidence
    assert bridge.features and bridge.testing_plan and bridge.deployment_plan and bridge.github_structure
    assert project_bridge.build_plan(bridge).status == "proposed"


def test_immutable_name_contact_education_dates_and_employment_context_survive_docx(tmp_path):
    raw = "Pratik Bugade\npratik@example.com | +91 9876543210 | github.com/pratik\n"
    facts = [
        fact("E1", "education", "B.Tech Computer Science", "Example University"),
        fact("X1", "experience_bullet", "Built Python APIs", "Example Corp - Backend Intern (Jun 2024 - Dec 2024)"),
    ]
    path = docx_builder.build(facts, [], ["Pratik Bugade", "pratik@example.com", "+91 9876543210", "github.com/pratik"], tmp_path / "immutable.docx")
    assert immutable_guard.validate_document(path, facts, raw) == []


def test_immutable_guard_rejects_direct_education_rewrite():
    facts = [fact("E1", "education", "B.Tech Computer Science", "Example University")]
    rewrite = Rewrite(fact_id="E1", original="B.Tech Computer Science", final="M.Tech AI", status="accepted")
    assert immutable_guard.validate_rewrites(facts, [rewrite])


def test_score_integrity_keeps_source_evidence_when_a_rewrite_drops_jd_terms():
    facts = [fact("P1", "project_bullet", "Built Python FastAPI APIs with Docker", "API Platform")]
    reqs = [requirement("R1", "Python", "python"), requirement("R2", "FastAPI", "fastapi"),
            requirement("R3", "Docker", "docker")]
    req_set, matches, _ = plan_for(facts, reqs)
    before = match_stage.run(req_set, facts, facts[0].text)[1].jd_alignment_score
    dropped = [fact("P1", "project_bullet", "Built Python APIs", "API Platform")]
    after = match_stage.run(req_set, dropped, dropped[0].text)[1].jd_alignment_score
    assert after < before
