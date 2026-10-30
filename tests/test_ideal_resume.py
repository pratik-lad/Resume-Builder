import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "api"))

from llm.client import clean_model_text  # noqa: E402
from pipeline import ideal_resume  # noqa: E402


def test_clean_model_text_removes_thinking_and_role_prefix():
    raw = "<think>private reasoning</think>\nAssistant: # Ideal Candidate\n\n## Skills"
    assert clean_model_text(raw) == "# Ideal Candidate\n\n## Skills"


def test_resume_builder_uses_candidate_as_foundation(monkeypatch):
    captured = {"calls": []}

    def fake_chat(**kwargs):
        captured["calls"].append(kwargs)
        captured.update(kwargs)
        return "# Existing Candidate\n\n## Professional Summary\nTailored profile"

    monkeypatch.setattr(ideal_resume, "chat", fake_chat)
    result = ideal_resume.generate("Python and FastAPI", "Existing background")

    assert result.startswith("# Existing Candidate")
    assert captured["temperature"] == 0.15
    assert "resume builder and job-tailoring engine" in captured["system"]
    assert "candidate foundation" in captured["system"]
    assert "college or university name remain verbatim" in captured["system"]
    assert "Every explicit JD requirement" in captured["system"]
    assert "silent quality check" in captured["system"]
    assert "Do not insert the target role as an additional" in captured["system"]
    assert "Each top-level section appears once" in captured["system"]
    assert "CANDIDATE RESUME" in captured["prompt"]
    assert "Existing background" in captured["prompt"]
    assert "Keep distinct jobs and projects structurally separate" in captured["calls"][0]["prompt"]
    assert "Python and FastAPI" in captured["prompt"]


def test_missing_sections_trigger_one_complete_revision(monkeypatch):
    calls = []
    outputs = ["# Candidate\n## Professional Summary\nBackend developer",
               "# Candidate\n## Professional Summary\nFull stack developer\n## Technical Skills\nNode.js, React\n## Selected Projects\n### New Project - Learning Platform\n## Education\nCollege"]
    monkeypatch.setattr(ideal_resume, "chat",
                        lambda **kwargs: (calls.append(kwargs) or outputs[len(calls) - 1]))
    result = ideal_resume.generate("Required: Node.js and React", "# Candidate\nCollege")
    assert len(calls) == 2
    assert "MISSING JD SKILLS" in calls[1]["prompt"]
    assert "exactly two new projects" in calls[1]["prompt"]
    assert "Node.js" in result and "React" in result


def test_jd_skills_outside_technical_skills_do_not_force_revision(monkeypatch):
    calls = []
    draft = "# Candidate\n## Professional Summary\nNode.js React developer\n## Technical Skills\nPython\n## Selected Projects\n### New Project\nNode.js React\n## Education\nCollege"
    outputs = [draft]
    monkeypatch.setattr(ideal_resume, "chat",
                        lambda **kwargs: (calls.append(kwargs) or outputs[len(calls) - 1]))
    assert ideal_resume.generate("Required: Node.js and React", "# Candidate\nCollege") == draft
    assert len(calls) == 1


def test_project_heading_alias_and_jd_aligned_name_do_not_trigger_repair(monkeypatch):
    draft = """# Candidate
## Profile Summary
Full stack developer
## Technical Skills
Node.js, React
## Projects
### New JD-Aligned Project
Node.js, React
## Education
College
"""
    calls = []
    monkeypatch.setattr(ideal_resume, "chat", lambda **kwargs: (calls.append(kwargs) or draft))
    assert ideal_resume.generate("Required: Node.js and React", "# Candidate\nCollege") == draft
    assert len(calls) == 1
