import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline import ideal_resume, optimize, output_coverage, render  # noqa: E402
from schemas import ExperienceEntry, Requirement, RequirementSet  # noqa: E402


def test_demo_governance_gap_completion_adds_context_without_changing_scoring():
    markdown = """# Candidate
## Professional Summary
Senior data platform engineer.
## Technical Skills
- Databricks Unity Catalog, schema administration, data governance
## Selected Projects
### Governed Analytics Platform
Technical:
- Built governed data pipelines.
Functional:
- Coordinated delivery.
## Education
University
"""
    requirements = [
        Requirement(req_id="R14", text="5 to 8 years of data engineering experience including "
                    "at least 2 years hands-on with Databricks.", type="qualification",
                    must_have=True, min_years=5,
                    canonical_skills=["data engineering", "databricks"]),
        Requirement(req_id="R15", text="Databricks Unity Catalog catalog/schema/table "
                    "administration and access control.", type="hard_skill", must_have=True,
                    canonical_skills=["databricks unity catalog", "schema administration",
                                      "table administration"]),
        Requirement(req_id="R25", text="Data governance and business glossary workflows.",
                    type="hard_skill", must_have=True,
                    canonical_skills=["data governance", "business glossary"]),
    ]
    completed = output_coverage.complete_demo_governance_gaps(markdown, requirements)
    assert output_coverage.evaluate(completed, requirements).required_percent == 100
    assert "5+ years of data engineering" in completed
    assert "table administration" in completed
    assert "business glossary" in completed
    assert "- Built governed data pipelines." in completed
    assert output_coverage.complete_demo_governance_gaps(completed, requirements) == completed


def test_legacy_demo_checklist_is_removed_without_changing_fabrication_mode():
    markdown = ("# Candidate\n## Selected Projects\n- Built a platform.\n\n"
                "## Additional Role Capabilities\n- Copied JD requirement.")
    cleaned = output_coverage.strip_demo_coverage_appendix(markdown)
    assert cleaned == "# Candidate\n## Selected Projects\n- Built a platform."
    assert output_coverage.strip_demo_coverage_appendix(cleaned) == cleaned


def test_demo_keeps_explicit_experience_threshold_without_employment_dates():
    markdown = "# Candidate\n## Professional Summary\nML engineer.\n## Technical Skills\nPython"
    requirements = [
        Requirement(req_id="R18", text="4+ years in machine learning or applied AI.",
                    type="qualification", must_have=True, min_years=4),
        Requirement(req_id="R33", text="Experience: 4+ Years", type="qualification",
                    must_have=True, min_years=4),
    ]
    completed = output_coverage.complete_demo_governance_gaps(markdown, requirements)
    assert "4+ years of machine learning or applied AI experience" in completed
    assert completed.count("4+ years") == 1
    assert output_coverage.evaluate(completed, requirements).required_percent == 100
    assert output_coverage.complete_demo_governance_gaps(completed, requirements) == completed


def test_final_text_coverage_keeps_missing_years_and_alternative_certification_distinct():
    requirements = [
        Requirement(req_id="R1", text="8+ years of Salesforce experience", type="qualification",
                    must_have=True, min_years=8, canonical_skills=["salesforce"]),
        Requirement(req_id="R2", text="Salesforce Application Architect and/or System Architect",
                    type="qualification", must_have=True, logic="any"),
        Requirement(req_id="R3", text="CTA preferred", type="qualification", must_have=False),
    ]
    markdown = "## Technical Skills\nSalesforce\n## Certifications\n- Salesforce Application Architect"
    result = output_coverage.evaluate(markdown, requirements)
    assert result.required_percent == 50
    assert result.preferred_percent == 0
    assert [item.present for item in result.items] == [False, True, False]
    alternate = output_coverage.evaluate("## Certifications\n- Salesforce System Architect", requirements)
    assert alternate.items[1].present
    assert "does not verify" in render.build_ideal_report(markdown, RequirementSet(
        jd_text="Salesforce architect", requirements=requirements))


def test_jd_client_is_not_added_as_employer_but_other_generated_roles_remain():
    generated = """# Alex Example
## Professional Summary
Architect profile.
## Professional Experience
### Senior DevOps Engineer | Example Health
Dates: 2024 - Present
- Built cloud systems.
### Salesforce B2B Solution Architect | Zensar Technologies
Dates: 2021 - Present
- Built Salesforce commerce systems.
### Solution Architect | Example Partner
Dates: 2023 - Present
- Delivered integrations.
## Selected Projects
### Commerce Platform
Title: Commerce Platform
Tools: Salesforce
## Education
University
"""
    source = "Alex Example\nExample Health (Feb, 2024 - Current):\nDesignation: Senior DevOps Engineer"
    entry = ExperienceEntry(entry_id="E1", company="Example Health",
                            role_title="Senior DevOps Engineer", start_date="Feb 2024",
                            end_date="Current", source_evidence=source)
    result = ideal_resume.finalize(generated, "Salesforce Architect\nClient - Zensar",
                                   [], [entry], resume_text=source, fabrication_mode="demo")
    experience = result.split("## Professional Experience", 1)[1].split("## Selected Projects", 1)[0]
    assert "Zensar" not in experience
    assert "Example Partner" in experience


def test_fabrication_mode_keeps_one_revision_only_when_it_improves_output(monkeypatch):
    draft = "# Candidate\n## Professional Summary\nCloud architect.\n## Education\nUniversity"
    improved = draft.replace("Cloud architect.", "Salesforce architect with 8+ years of Salesforce experience.")
    calls = []
    monkeypatch.setattr(optimize.ideal_resume, "generate", lambda *args: draft)
    monkeypatch.setattr(optimize.ideal_resume, "revise_for_coverage",
                        lambda *args: (calls.append(args) or improved))
    requirements = [Requirement(req_id="R1", text="8+ years of Salesforce experience",
                                type="qualification", must_have=True, min_years=8,
                                canonical_skills=["salesforce"])]
    result = optimize.optimize([], requirements, [], set(), jd_text="8+ years of Salesforce experience",
                               resume_text="Candidate\nUniversity", fabrication_mode="demo")
    assert len(calls) == 1
    assert result.output_coverage.required_percent == 100
    assert result.fabrication_mode == "demo"
    assert "8+ years" in result.markdown


def test_compound_databricks_requirements_show_partial_and_missing_components():
    markdown = """# Candidate
## Professional Summary
Data Engineering and Databricks platform specialist.
## Technical Skills
- **Governance:** Unity Catalog, Schema Administration, access control
## Professional Experience
### Data Engineer | Example
- Configured Unity Catalog schemas and access control for certified tables.
"""
    requirements = [
        Requirement(req_id="R14", text="5 to 8 years of data engineering experience including "
                    "at least 2 years hands-on with Databricks.", type="qualification",
                    must_have=True, min_years=5,
                    canonical_skills=["data engineering", "databricks"]),
        Requirement(req_id="R15", text="Databricks Unity Catalog including schema/table administration "
                    "and access control.", type="hard_skill", must_have=True,
                    canonical_skills=["unity catalog", "schema administration", "table administration"]),
    ]
    result = output_coverage.evaluate(markdown, requirements)
    assert [item.status for item in result.items] == ["partial", "partial"]
    assert "table administration" in result.items[1].missing_components
    assert any("2+ years" in part for part in result.items[0].missing_components)
    html = render.build_ideal_report(markdown, RequirementSet(jd_text="Databricks", requirements=requirements))
    assert "Partial" in html and "Missing: table administration" in html
