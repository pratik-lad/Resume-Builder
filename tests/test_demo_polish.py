import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline import demo_polish, ideal_resume  # noqa: E402
from schemas import ExperienceEntry  # noqa: E402


def test_sales_demo_gets_dated_role_and_specific_work_without_appendix():
    markdown = """# Candidate
## Professional Summary
10+ years of technology sales.
## Technical Skills
Salesforce
## Professional Experience
### Confidential | Lead MLOps Engineer
Dates: Feb 2024 - Present
- Ran platforms.
### Senior Business Development Manager | Example Consulting
- Led sales.
## Selected Projects
### Enterprise RFP Platform
- Prepared proposals.
### Generic Quality and Reliability Platform
- Ran checks.
## Education
BTech
## Certifications
- Professional Certificate in Senior Business Development Manager
"""
    jd = "Senior Business Development Manager - B2B Technology Sales\n7+ years of B2B sales"
    result = demo_polish.polish(markdown, jd)
    assert re.search(r"### Senior Business Development Manager \| Example Consulting\nDates: Jan \d{4} - Present", result)
    assert "Statements of Work (SOW)" in result
    assert "renewals, upselling, and cross-selling" in result
    assert "### Strategic Accounts and Partner Expansion" in result
    assert "### Lead MLOps Engineer | Confidential" in result
    assert "Additional Role Capabilities" not in result
    assert demo_polish.polish(result, jd) == result


def test_salesforce_demo_uses_named_credentials_and_removes_malformed_role():
    markdown = """# Candidate
## Professional Experience
### Sept | Example Cloud Engineer
Dates: 2021 - 2022
- Placeholder.
### DevOps Engineer | Example
Dates: 2022 - Present
- Built deployments.
## Selected Projects
### B2B Commerce Storefront
- Built cart.
### Cloud-Native Observability Suite
- Monitored services.
## Education
BTech
## Certifications
- Professional Certificate in Salesforce B2B Solution Architect
- Advanced Certificate in Apex
"""
    jd = "Salesforce B2B Solution Architect\nB2B Commerce and CPQ / Revenue Cloud"
    result = demo_polish.polish(markdown, jd)
    assert "### Sept |" not in result
    assert "### Salesforce B2B Solution Architect | Enterprise Commerce Consulting" in result
    assert "checkout, order management" in result
    assert "### Revenue Cloud Quote-to-Cash Architecture" in result
    assert "- Salesforce Application Architect" in result
    assert "- Salesforce CPQ Specialist" in result
    assert "- Salesforce Certified Technical Architect (CTA)" in result
    assert "Professional Certificate in Salesforce" not in result
    assert demo_polish.polish(result, jd) == result


def test_malformed_experience_entries_do_not_become_job_headings():
    bad = ExperienceEntry(entry_id="E1", company="Sept", role_title="AWS Engineer",
                          start_date="2021", source_evidence="Sept 2021")
    good = ExperienceEntry(entry_id="E2", company="Confidential",
                           role_title="Lead MLOps Engineer", start_date="Feb 2024",
                           source_evidence="Lead MLOps Engineer")
    assert not ideal_resume._valid_experience_entry(bad)
    assert ideal_resume._valid_experience_entry(good)
