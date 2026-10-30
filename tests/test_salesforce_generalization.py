import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline import ideal_resume, jd  # noqa: E402
from schemas import Requirement  # noqa: E402


def test_jd_curation_keeps_alternative_certification_and_drops_logistics():
    description = """Salesforce B2B Solution Architect
Mandatory Skills:
8+ years of Salesforce experience.
Certifications:
Salesforce Application Architect and/or System Architect – Required
CTA – Preferred
Important Pointers
UAN is mandatory for all candidates.
"""
    items = [
        dict(text="Have at least 8 years of Salesforce experience.", type="qualification",
             must_have=True, min_years=8, canonical_skills=[]),
        dict(text="8+ years of Salesforce experience.", type="qualification",
             must_have=True, min_years=8, canonical_skills=[]),
        dict(text="Possess Salesforce Application Architect certification.", type="qualification",
             must_have=True, min_years=0, canonical_skills=[]),
        dict(text="Possess Salesforce System Architect certification.", type="qualification",
             must_have=True, min_years=0, canonical_skills=[]),
        dict(text="Have a UAN (Universal Account Number).", type="qualification",
             must_have=True, min_years=0, canonical_skills=[]),
    ]
    result = jd._curate_requirements(items, description)
    texts = [item["text"] for item in result]
    assert sum("years" in text for text in texts) == 1
    assert sum("Application Architect" in text for text in texts) == 1
    assert sum("System Architect" in text for text in texts) == 1
    assert not any("UAN" in text for text in texts)
    assert result[-1]["logic"] == "any"


def test_finalizer_recovers_project_rows_and_keeps_only_two_added_projects():
    source = """Taylor Example
DevOps Engineer
Technologies | Tools
DevOps | Terraform, Jenkins, Kubernetes
Languages | Python
Degree | Institute | PERCENTAGE
MCA | Example University | 65%
#Confidential (Feb,2025 - Present)
Project : Source Deployment Platform
Designation: DevOps Engineer
Title: | Source Deployment Platform
Client: | Product
Project Description: | Built a deployment platform.
"""
    draft = """# Taylor Example
Salesforce B2B Solution Architect
## Professional Summary
Architecture summary.
## Professional Experience
### DevOps Engineer | Confidential
- Built platforms.
## Selected Projects
### Generic Cloud Platform
Title: Generic Cloud Platform
Tools: AWS
### Salesforce B2B Commerce Platform
Title: Salesforce B2B Commerce Platform
Tools: Apex, LWC
### Salesforce CPQ Platform
Title: Salesforce CPQ Platform
Tools: CPQ, Revenue Cloud
## Education
MCA | Example University | 65%
"""
    reqs = [Requirement(req_id="R1", text="Apex and LWC", type="hard_skill",
                        must_have=True, canonical_skills=["apex", "lwc"])]
    output = ideal_resume.finalize(draft, "Salesforce B2B Solution Architect\nApex, LWC, CPQ",
                                   reqs, resume_text=source, fabrication_mode="demo")
    projects = output.split("## Selected Projects", 1)[1].split("## Education", 1)[0]
    assert projects.count("### ") == 3
    assert "### Source Deployment Platform" in projects
    assert "### Salesforce B2B Commerce Platform" in projects
    assert "### Salesforce CPQ Platform" in projects
    assert "### Generic Cloud Platform" not in projects
    assert "Built a deployment platform" in projects
    assert "Terraform" in output.split("## Technical Skills", 1)[1]


def test_year_range_uses_lower_bound_and_deduplicates_rephrased_requirement():
    first = "Possess 5 to 8 years of data engineering experience including at least 2 years hands-on with Databricks."
    repeated = "5–8 years of data engineering experience, including at least 2 years hands-on with Databricks."
    rows = jd._curate_requirements([
        dict(text=first, type="qualification", must_have=True, min_years=5,
             canonical_skills=["data engineering", "databricks"]),
        dict(text=repeated, type="qualification", must_have=True, min_years=8,
             canonical_skills=[]),
    ], first + "\n" + repeated)
    assert len(rows) == 1
    assert rows[0]["min_years"] == 5
    extracted = jd._numeric_experience_requirements(repeated)
    assert extracted[0]["min_years"] == 5
