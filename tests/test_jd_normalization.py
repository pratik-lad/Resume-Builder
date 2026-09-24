import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline import jd  # noqa: E402
from schemas import ExtractedRequirement, ExtractedRequirements  # noqa: E402


def test_extraction_prompt_requires_full_jd_self_check():
    from pipeline.prompts import render
    prompt = render("jd_extraction.jinja", jd_text="Python and stakeholder communication")
    assert "Extract ALL required and preferred expectations" in prompt
    assert "silently compare" in prompt
    assert "every sentence and" in prompt


def test_production_jd_preserves_alternatives(monkeypatch):
    output = ExtractedRequirements(requirements=[ExtractedRequirement(
        text="AWS / Azure / GCP", type="tool", must_have=True,
        skills=["AWS", "Azure", "GCP"])])
    monkeypatch.setattr(jd.structured, "generate", lambda *args, **kwargs: output)
    reqs = jd.extract("Required: AWS / Azure / GCP").requirements
    assert len(reqs) == 1
    assert reqs[0].logic == "any"
    assert reqs[0].canonical_skills == ["aws", "azure", "gcp"]


def test_production_jd_splits_combined_named_skills(monkeypatch):
    output = ExtractedRequirements(requirements=[ExtractedRequirement(
        text="Docker and Kubernetes", type="tool", must_have=False,
        skills=["Docker", "Kubernetes"])])
    monkeypatch.setattr(jd.structured, "generate", lambda *args, **kwargs: output)
    reqs = jd.extract("Nice to have: Docker and Kubernetes").requirements
    assert [r.text for r in reqs] == ["Docker", "Kubernetes"]
    assert all(not r.must_have for r in reqs)
    assert all(r.source_text == "Docker and Kubernetes" for r in reqs)


def test_jd_title_falls_back_to_first_line_when_local_model_omits_it(monkeypatch):
    monkeypatch.setattr(jd.structured, "generate", lambda *args, **kwargs: ExtractedRequirements())
    output = jd.extract("GenAI Engineer\nRequired: Python and FastAPI")
    assert output.role_title == "GenAI Engineer"


def test_vidyalai_style_jd_recovers_requirements_omitted_by_model(monkeypatch):
    model_output = ExtractedRequirements(role_title="About the job", requirements=[
        ExtractedRequirement(text="Develop highly available and scalable REST API endpoints.",
                             type="responsibility", skills=["REST API"]),
    ])
    monkeypatch.setattr(jd.structured, "generate", lambda *args, **kwargs: model_output)
    text = """About the job
Position Overview: As a Full stack Developer at Vidyalai.com, you will build the platform.
Responsibilities:
Write clean modular code using Node.js, Express.js, WebSockets, MongoDB, and ReactJS.
Take conceptual ideas into production by designing, building, testing, and deploying applications.
Develop highly available and scalable REST API endpoints.
Skills Required:
Deep understanding in computer science.
Extra credit if you know Next.js, Redux, Nest.js, and Socket.io.
Who Can Apply:
1+ years of experience in the relevant field.
Has a passion for software development demonstrated through side projects or internships.
Please do not apply if you do not meet the criteria."""
    result = jd.extract(text)
    joined = "\n".join(item.text for item in result.requirements).casefold()
    assert result.role_title == "Full stack Developer"
    for expected in ("node.js", "conceptual ideas", "computer science", "next.js",
                     "1+ years", "side projects"):
        assert expected.casefold() in joined
    assert len(result.requirements) >= 7


def test_unknown_named_technology_is_retained_from_a_jd_skill_cue(monkeypatch):
    monkeypatch.setattr(jd.structured, "generate", lambda *args, **kwargs: ExtractedRequirements())
    output = jd.extract("Required Skills:\nExperience with Temporal, Supabase, and React.js.")
    skills = {skill for requirement in output.requirements for skill in requirement.canonical_skills}
    assert {"temporal", "supabase", "react"} <= skills


def test_numeric_experience_requirement_is_retained_outside_a_heading(monkeypatch):
    monkeypatch.setattr(jd.structured, "generate", lambda *args, **kwargs: ExtractedRequirements())
    output = jd.extract("We need a Full Stack Developer with 6+ years of React.js and Node.js experience.")
    numeric = [item for item in output.requirements if item.min_years == 6]
    assert numeric
    assert "6+ years" in numeric[0].text
