import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from config import settings
from matching import normalizer, technology_catalog
from pipeline import ideal_resume
from pipeline.skill_layout import format_skills


def test_versioned_catalog_includes_baseline_and_reviewed_role_families():
    entries = technology_catalog.snapshot()["entries"]
    assert len(entries) >= 179
    names = {item["name"] for item in entries}
    assert {"Databricks Unity Catalog", "Databricks Genie", "Salesforce CPQ",
            "Apex", "Delta Lake", "PySpark", "Microsoft Fabric",
            "Microsoft Foundry", "React", "Playwright"} <= names
    assert len({item["category"] for item in entries}) >= 8


def test_catalog_names_join_existing_matching_without_overriding_old_aliases():
    assert normalizer.canonical("Unity Catalog") == "databricks unity catalog"
    assert normalizer.canonical("Genie") == "databricks genie"
    assert normalizer.canonical("LWC") == "lightning web components"
    assert normalizer.canonical("PySpark") == "spark"  # existing alias wins
    assert normalizer.canonical("Postgres") == "postgresql"
    assert "databricks unity catalog" in normalizer.canonical_skills_in_text(
        "Govern tables with Unity Catalog and query with Genie.")


def test_only_matched_reviewed_terms_enter_bounded_context():
    jd = "Use Unity Catalog, Genie, Salesforce CPQ, Apex, LWC and Delta Lake."
    context = technology_catalog.context_for_jd(jd, max_chars=440)
    assert len(context) <= 440
    assert "Unity Catalog" in context
    assert "candidate evidence" in context
    assert "React" not in context
    assert not technology_catalog.context_for_jd("Unrelated role with no named tools")


def test_catalog_groups_new_jd_tools_and_keeps_source_skills():
    jd = "**Data tools:** Unity Catalog, Databricks Genie, Delta Lake"
    source = "Candidate\nSKILLS\nPython, Terraform\nEDUCATION\nDegree"
    result = format_skills(jd, source, [])
    for term in ("Databricks Unity Catalog", "Databricks Genie", "Delta Lake",
                 "Python", "Terraform"):
        assert term in result
    assert all(line.startswith("- **") and ":** " in line for line in result.splitlines())
    assert "QuantumWidgets" in format_skills("**Tools:** QuantumWidgets", source, [])


def test_audit_reports_legacy_collisions_unreviewed_and_staleness():
    report = technology_catalog.audit("Required tools: Unity Catalog and PySpark")
    assert report["duplicates"]
    assert any(item["surface"] == "PySpark" for item in report["alias_conflicts"])
    assert report["unverified"]  # imported baseline is not source-verified
    assert "Databricks Unity Catalog" not in report["unverified"]
    assert "Databricks Unity Catalog" in technology_catalog.audit(today=date(2027, 6, 1))["stale"]


def test_generation_toggle_preserves_fabrication_prompt_and_one_call(monkeypatch):
    calls = []
    draft = "# Candidate\n## Professional Summary\nSummary\n## Technical Skills\nApex\n## Selected Projects\n### One\n## Education\nCollege"
    monkeypatch.setattr(ideal_resume, "chat", lambda **kwargs: (calls.append(kwargs) or draft))
    monkeypatch.setattr(settings, "catalog_enabled", True)
    ideal_resume.generate("Required: Apex and Salesforce CPQ", "Candidate\nExisting work")
    assert len(calls) == 1
    assert "TECHNOLOGY REFERENCE" in calls[0]["prompt"]
    assert "You may fabricate plausible additional experience" in calls[0]["system"]
    monkeypatch.setattr(settings, "catalog_enabled", False)
    ideal_resume.generate("Required: Apex and Salesforce CPQ", "Candidate\nExisting work")
    assert len(calls) == 2
    assert "TECHNOLOGY REFERENCE" not in calls[1]["prompt"]
    assert calls[0]["system"] == calls[1]["system"]
