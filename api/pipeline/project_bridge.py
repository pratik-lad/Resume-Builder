"""Future-work project bridge, always isolated from current resume evidence."""
import re

from schemas import (OptimizationStrategy, ProjectBuildPlan, ProposedProject,
                     Requirement, RequirementSet)


def _unique(values):
    return list(dict.fromkeys(v for v in values if v))


def recommend(req_set: RequirementSet, strategy: OptimizationStrategy) -> ProposedProject | None:
    by_id = {r.req_id: r for r in req_set.requirements}
    # A portfolio project can demonstrate a technical skill/tool or a concrete
    # implementation responsibility. It cannot create professional years,
    # a degree, a certification, or another qualification claim.
    missing = [c for c in strategy.coverage
               if c.status == "missing" and c.importance in {"critical", "high"}
               and by_id[c.req_id].type in {"hard_skill", "tool", "responsibility"}
               and by_id[c.req_id].min_years == 0]
    if not missing:
        return None
    selected = missing[:8]
    requirements = [by_id[c.req_id] for c in selected]
    technologies = _unique(skill for req in requirements for skill in req.canonical_skills)[:10]
    role = req_set.role_title.strip() or "Target Role"
    safe_role = re.sub(r"[^A-Za-z0-9 +#.-]", "", role).strip()
    title = f"{safe_role} Capability Bridge" if safe_role else "JD Capability Bridge"
    architecture = [
        "User or source-data interface",
        "Core application/service layer",
        "Persistence or integration layer",
        "Automated tests and validation",
        "Containerized local deployment",
    ]
    if technologies:
        architecture.insert(2, "JD-relevant technology layer: " + ", ".join(technologies))
    req_text = [r.text for r in requirements]
    features = [f"Implement and test a capability mapped to: {text}" for text in req_text[:6]]
    return ProposedProject(
        project_id="PROJECT-BRIDGE-01", title=title, status="proposed",
        eligible_as_resume_evidence=False,
        problem_statement=("Build a portfolio project that demonstrates the highest-impact currently missing "
                           f"requirements for {role}, without claiming professional experience."),
        why_it_matches_jd="It targets the largest required gaps identified by requirement-level matching.",
        technologies=technologies, architecture=architecture,
        features=features,
        requirements_covered=req_text, skills_demonstrated=technologies,
        expected_resume_bullets=[
            "After completion: describe what was actually implemented and verified.",
            "After measurement: add only source-supported tests, scale, latency, or quality results.",
        ],
        implementation_roadmap=[
            "Define acceptance criteria mapped to the selected JD requirements.",
            "Create a minimal working vertical slice with tests.",
            "Integrate the remaining selected technologies one at a time.",
            "Add validation, observability, documentation, and reproducible setup.",
            "Verify the completed repository and only then derive resume evidence.",
        ],
        testing_plan=[
            "Unit-test each core requirement-mapped capability.",
            "Add an end-to-end test for the primary user workflow.",
            "Record only measured results that can be reproduced from the repository.",
        ],
        deployment_plan=[
            "Containerize the verified application.",
            "Document local setup and a reproducible deployment path.",
            "Do not claim deployment until it has actually occurred and is documented.",
        ],
        github_structure=["README.md", "src/", "tests/", "docs/architecture.md", "Dockerfile", ".env.example"],
        estimated_difficulty="advanced" if len(technologies) >= 6 else "intermediate",
        portfolio_value="High if completed, tested, documented, and independently verifiable.")


def build_plan(project: ProposedProject) -> ProjectBuildPlan:
    tech = ", ".join(project.technologies) or "the selected implementation stack"
    return ProjectBuildPlan(
        project_id=project.project_id, status=project.status,
        folder_structure=project.github_structure or ["README.md", "src/", "tests/", "docs/architecture.md", "Dockerfile", ".env.example"],
        readme=(f"# {project.title}\n\nStatus: Proposed - Not Yet Completed\n\n"
                f"Target stack: {tech}\n\nThis repository begins as a scaffold. Do not present it as completed evidence."),
        implementation_plan=project.implementation_roadmap,
        files={
            "src/__init__.py": "\"\"\"Application package. Implement and verify before claiming completion.\"\"\"\n",
            "tests/test_smoke.py": "def test_scaffold_is_explicitly_incomplete():\n    assert True\n",
            "Dockerfile": "FROM python:3.11-slim\nWORKDIR /app\nCOPY . .\nCMD [\"python\", \"-m\", \"src\"]\n",
            ".env.example": "# Add non-secret configuration keys here.\n",
        },
        setup_instructions=["Create a virtual environment.", "Install declared dependencies.",
                            "Run the test suite.", "Build and run the Docker image."],
        tests=project.testing_plan or ["Unit tests for core logic", "Integration test for the main workflow",
                                       "Validation tests for each claimed JD requirement"],
        resume_evidence_warning=("PROPOSED PROJECT - NOT YET COMPLETED. This scaffold is not resume evidence. "
                                 "Only verified completed work may be re-ingested as candidate evidence."))


def with_status(project: ProposedProject, status: str,
                verification_evidence: list[str]) -> ProposedProject:
    if status == "verified" and not verification_evidence:
        raise ValueError("verified status requires verification evidence")
    return project.model_copy(update={
        "status": status, "verification_evidence": verification_evidence,
        "eligible_as_resume_evidence": status == "verified" and bool(verification_evidence),
    })
