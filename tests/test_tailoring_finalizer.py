import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "api"))
from pipeline.ideal_resume import finalize
from schemas import ExperienceEntry, Requirement


def test_finalizer_enforces_targeted_sections_and_moves_new_project():
    draft = """# Pratik Bugade
Target Role: Full Stack Developer
## Profile Summary
Old GenAI summary.
## Projects
### Existing Project
- Existing work
## Technical Skills
- Python, FastAPI
## Education
D. Y. Patil Agriculture and Technical University
D. Y. Patil Agriculture and Technical University
## New Project
### Learning Platform
- React work
Return only the completed resume as valid Markdown.
"""
    requirements = [
        Requirement(req_id="R1", text="Build applications with Node.js and ReactJS",
                    type="responsibility", must_have=True,
                    canonical_skills=["nodejs", "react"]),
        Requirement(req_id="R2", text="Develop scalable REST API endpoints",
                    type="responsibility", must_have=True,
                    canonical_skills=["rest api"]),
        Requirement(req_id="R3", text="Preferred Redux, Nest.js, and Socket.io",
                    type="hard_skill", must_have=False),
    ]
    result = finalize(draft, "As a Full stack Developer at Vidyalai.com", requirements)
    assert result.count("## Professional Summary") == 1
    assert "Full stack Developer focused on" in result
    skills = result.split("## Technical Skills", 1)[1].split("## ", 1)[0]
    assert all(item in skills for item in ("Node.js", "ReactJS", "REST APIs", "Redux", "Nest.js", "Socket.io"))
    assert result.index("### Learning Platform") < result.index("## Education")
    assert result.index("### Learning Platform") < result.index("### JD-Aligned Project: Target Solution")
    assert "## New Project" not in result
    assert "Return only" not in result
    assert "D. Y. Patil Agriculture and Technical University" in result
    assert result.count("D. Y. Patil Agriculture and Technical University") == 1


def test_finalizer_removes_repair_narration_and_qa_blocks():
    draft = """# Candidate
## Professional Summary
Developer
## Technical Skills
Node.js
## Selected Projects
### New JD-Aligned Project
- Built a platform
## Education
College
The new project is missing, so I added it in the Selected Projects section before Education:
# Missing Sections
- None
# New Project Misplaced or Missing
- Yes
"""
    result = finalize(draft, "Full Stack Developer", [])
    assert "The new project is missing" not in result
    assert "Missing Sections" not in result
    assert "New Project Misplaced or Missing" not in result


def test_finalizer_replaces_source_employment_with_labeled_fictional_demo():
    draft = """# Candidate
## Professional Experience
### Full Stack Engineer at Oteemo
- Invented JD responsibilities
## Selected Projects
### Existing Project
- Work
## Education
College
"""
    entries = [ExperienceEntry(
        entry_id="EXP-DATE-01", company="ABC Technologies", role_title="Software Developer",
        start_date="May 2022", end_date="", current=True,
        source_evidence="Software Developer | ABC Technologies | May 2022 – Present",
    )]
    result = finalize(draft, "Full Stack Developer", [], entries)
    assert "**DEMO / FICTIONAL RESUME" not in result
    assert "## Professional Experience" in result
    assert "### Software Developer | ABC Technologies" in result
    assert "Dates: [MM/YYYY - MM/YYYY or Present]" in result
    assert "ABC Technologies" in result
    assert "Oteemo" not in result
    return
    experience = result.split("## Professional Experience", 1)[1].split("## Selected Projects", 1)[0]
    assert "Total Professional Experience:" in experience
    assert "### Software Developer | ABC Technologies" in experience
    assert "May 2022 – Present" in experience
    assert "Oteemo" not in result
    assert "Invented JD responsibilities" not in result


def test_finalizer_ignores_undated_source_employment_in_demo_mode():
    draft = """# Candidate
## Professional Experience
### Target Company | Full Stack Engineer
- Generated work
## Education
College
"""
    entries = [ExperienceEntry(entry_id="EXP-UNDATED-01", company="ABC Technologies",
                               role_title="Software Developer",
                               source_evidence="ABC Technologies | Software Developer")]
    result = finalize(draft, "Full Stack Developer", [], entries)
    assert "## Professional Experience" in result
    assert "### Software Developer | ABC Technologies" in result
    assert "Dates: [MM/YYYY - MM/YYYY or Present]" in result
    assert "ABC Technologies" in result
    assert "Target Company" not in result
    return
    assert "### Software Developer | ABC Technologies" in result
    assert "Dates: Please update with your actual employment dates" in result
    assert "Target Company" not in result
