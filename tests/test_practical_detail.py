import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline import ideal_resume, optimize, practical_detail
from schemas import ExperienceEntry, Requirement


WEAK = """# Candidate
## Professional Summary
Engineer with customer delivery experience.
## Technical Skills
Python, FastAPI
## Professional Experience
### Engineer | Source Corp
- Responsible for key projects.
- Worked with teams to deliver solutions.
- Built software for customers.
## Selected Projects
### Service Platform
- Developed solutions for users.
- Supported teams and operations.
- Handled technical requirements.
## Education
University
"""

STRONG = """# Candidate
## Professional Summary
Engineer with customer delivery experience.
## Technical Skills
Python, FastAPI
## Professional Experience
### Engineer | Source Corp
- Designed a FastAPI service with request validation and database transactions, then deployed it for customer onboarding.
- Implemented retry handling for downstream API failures and tested recovery with integration scenarios before release.
- Monitored production latency and improved the query path after reviewing customer feedback.
## Selected Projects
### Service Platform
- Built a Python pipeline that validated incoming customer records and routed failed batches to a review queue.
- Integrated the service with a PostgreSQL database and tested schema migrations before deployment.
- Deployed the application behind health checks and monitored failed requests during rollout.
## Education
University
"""


def _run(monkeypatch, draft, revision=None):
    calls = []
    monkeypatch.setattr(ideal_resume, "generate", lambda *_: draft)
    monkeypatch.setattr(ideal_resume, "finalize", lambda markdown, *_args, **_kwargs: markdown)
    def revise(*args):
        calls.append(args)
        return revision or draft
    monkeypatch.setattr(ideal_resume, "revise_for_practical", revise)
    debug = {}
    result = optimize.optimize([], [Requirement(req_id="R1", text="Python and FastAPI",
                                               type="hard_skill", must_have=True,
                                               canonical_skills=["python", "fastapi"])],
                               [], set(), jd_text="Forward Deployed AI Engineer: Python and FastAPI",
                               resume_text="Candidate\nEngineer at Source Corp",
                               fictional_template=True, fabrication_mode="demo",
                               allow_unverified=True, debug=debug)
    return result, debug, calls


def test_weak_draft_gets_one_practical_revision_without_reducing_fabrication(monkeypatch):
    result, debug, calls = _run(monkeypatch, WEAK, STRONG)
    assert len(calls) == 1
    assert debug["practical_revision_attempted"] is True
    assert debug["practical_revision_accepted"] is True
    assert "request validation and database transactions" in result.markdown
    assert "## Selected Projects" in result.markdown
    assert result.fabrication_mode == "demo" and result.allow_unverified is True
    assert "#Confidential" not in result.markdown.split("## Selected Projects")[0]
    assert "match score" not in result.markdown.casefold()


def test_strong_draft_skips_extra_model_call(monkeypatch):
    result, debug, calls = _run(monkeypatch, STRONG)
    assert calls == []
    assert debug["practical_revision_attempted"] is False
    assert "request validation and database transactions" in result.markdown


def test_revision_that_loses_covered_skill_is_rejected(monkeypatch):
    candidate = STRONG.replace("Python, FastAPI", "Go").replace("FastAPI service", "backend service")
    result, debug, calls = _run(monkeypatch, WEAK, candidate)
    assert len(calls) == 1
    assert debug["practical_revision_accepted"] is False
    assert "Responsible for key projects" in result.markdown


def test_detailed_bullets_survive_experience_compaction():
    generated = """### Engineer | Added Corp
- Worked on relevant technologies.
- Supported projects and teams.
- Designed a FastAPI service with request validation and database transactions, then deployed it for onboarding.
- Integrated customer API data with a PostgreSQL schema and tested migration failures before release.
"""
    compact = ideal_resume._compact_experience(generated, [], "", [], "Python FastAPI")
    assert "request validation and database transactions" in compact
    assert "PostgreSQL schema" in compact
    assert len([line for line in compact.splitlines() if line.startswith("- ")]) == 3


def test_text_role_recovery_when_structured_entries_are_malformed():
    source = """Candidate
Source Corp (Jan 2020 - Dec 2023):
Designation: Engineer
- Built Python data pipelines for model training.
"""
    malformed = [ExperienceEntry(entry_id="BAD-1", company="", role_title="Engineer",
                                 source_evidence="malformed parser entry")]
    result = ideal_resume.finalize(WEAK, "Python Engineer", [], malformed,
                                   resume_text=source)
    assert "### Engineer | Source Corp" in result


def test_practical_prompt_keeps_full_demo_scope(monkeypatch):
    captured = {}
    monkeypatch.setattr(ideal_resume, "chat", lambda **kwargs: captured.update(kwargs) or STRONG)
    ideal_resume.revise_for_practical(WEAK, "Python delivery", "Candidate", ("More ownership",))
    assert "plausible additional roles, projects, responsibilities, certifications, scope, and metrics" in captured["prompt"]
    assert "candidate owned" in ideal_resume.SYSTEM_PROMPT
    assert not practical_detail.assess(STRONG).needs_revision
    assert practical_detail.assess(WEAK).needs_revision


def test_quality_check_flags_placeholders_and_generic_projects():
    resume = """# Candidate
## Professional Experience
### #Confidential Employer | Senior AI Engineer
- Address AI agent ownership.
## Selected Projects
### Target Role Delivery and Integration Platform
Project Description: Built a distinct part of the target role's workflow.
- Designed a workflow for repeatable execution.
## Education
University
"""
    assessment = practical_detail.assess(resume)
    assert assessment.needs_revision
    assert assessment.critical_defects


@pytest.mark.parametrize("role,bullets", [
    ("Data Analyst", [
        "Built SQL models that reconciled customer metrics and validated dashboard totals before stakeholder release.",
        "Designed a Power BI dashboard with drill-down measures and tested refresh failures during rollout.",
        "Monitored production data freshness and investigated missing records with operations stakeholders.",
    ]),
    ("Business Development Manager", [
        "Built a CRM account workflow that tracked customer discovery and validated forecast assumptions with sales leadership.",
        "Negotiated customer contracts through a documented review process and delivered agreed implementation milestones.",
        "Monitored conversion metrics and revised account plans after stakeholder feedback improved pipeline quality.",
    ]),
])
def test_practical_check_applies_across_roles(role, bullets):
    body = "\n".join(f"- {bullet}" for bullet in bullets)
    resume = (f"# Candidate\n## Professional Experience\n### {role} | Added Corp\n{body}\n"
              f"## Selected Projects\n### Customer Delivery\n{body}\n## Education\nUniversity")
    assert practical_detail.assess(resume).needs_revision is False


def test_confidential_source_roles_recover_original_bullets():
    source = """PROFESSIONAL EXPERIENCE
Senior AI Engineer | #confidential
Whisper (ASR Platform) — Healthcare speech-to-text platform
• Own end-to-end development of an AI speech-to-text solution, taking models into production.
• Reduced infrastructure cost by 20x by building traffic-based autoscaling for Kubernetes.
Associate Software Engineer (Platform Engineer) | #confidential
Xpresso.ai — Enterprise MLOps platform
• Built AWS infrastructure with Terraform for enterprise ML workloads.
EDUCATION
B.Tech
"""
    entry = ExperienceEntry(entry_id="source", company="#Confidential",
                            role_title="Senior AI Engineer", source_evidence="source header")
    bullets = ideal_resume._source_role_bullets(source, entry)
    assert len(bullets) == 2
    assert any("speech-to-text solution" in bullet for bullet in bullets)
    assert all("Address AI agent ownership" not in bullet for bullet in bullets)


def test_practical_check_flags_copied_jd_duty_text():
    jd = "Implement human review and approval controls for high-impact AI decisions."
    resume = """# Candidate
## Professional Experience
### AI Engineer | #Confidential
- Implement human review and approval controls for high-impact AI decisions.
## Selected Projects
### AI Quality Review
- Routed low-confidence predictions to a quality-engineer queue and validated results before release.
## Education
B.Tech
"""
    report = practical_detail.assess(resume, jd)
    assert report.needs_revision
    assert any("copies a JD duty" in defect for defect in report.critical_defects)


def test_ai_generic_project_fallback_is_replaced_with_specific_delivery_example():
    jd = """Artificial Intelligence (AI)
Design, develop, test, deploy and maintain AI solutions.
Implement human review and approval controls for high-impact AI decisions.
Govern AI agents with ownership, identities, permissions, lifecycle management, and observability.
"""
    result = ideal_resume._project_detail(
        "Target Role Delivery and Integration Platform",
        "Project Description: Built a distinct part of the target role's workflow.", jd, [], 0)
    assert "Enterprise AI Agent Governance and Observability" in result
    assert "Microsoft Entra ID" in result and "OpenTelemetry" in result
    assert "distinct part of the target role" not in result


def test_ai_certification_fallback_uses_named_relevant_credentials():
    certs = ideal_resume._additional_certifications("Azure AI and AI agent development", "AI Engineer")
    assert certs == [
        "- Microsoft Certified: Azure AI Apps and Agents Developer Associate",
        "- Microsoft Certified: Azure AI Fundamentals",
    ]
