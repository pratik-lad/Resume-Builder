import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "api"))
from pipeline.skill_layout import _source_skill_items, format_skills


def test_jd_skills_lead_and_all_structured_source_skills_remain():
    source = """Candidate
TECHNICAL SKILLS
Languages | Python, Scala, Bash
Big Data | Apache Spark, Apache Iceberg, Presto/Trino
Cloud | AWS (S3, Glue, EMR), Terraform
EDUCATION
Degree
"""
    jd = """# Job Title: Senior Data Analyst
## Required Technical Environment
**BI & Visualization:** Power BI, Tableau
**Programming & Analysis:** Python, SQL
"""
    output = format_skills(jd, source, [])
    assert output.splitlines()[0].startswith("- **Analytics & BI:** Power BI, Tableau")
    for term in ("Python", "SQL", "Scala", "Bash", "Apache Spark", "Apache Iceberg",
                 "Presto/Trino", "AWS (S3, Glue, EMR)", "Terraform"):
        assert term in output
    assert all(line.startswith("- **") and ":** " in line for line in output.splitlines())
    assert "|" not in output


def test_flat_pdf_skills_keep_tools_but_not_table_labels():
    source = """Candidate
SKILLS
Technologies
Tools
Terraform, Kubernetes(EKS,
DevOps
GKE, AKS), Vault, Chaos
Engineering, Istio
Languages
Python, Go
EDUCATION
Degree
"""
    items = [term for term, _ in _source_skill_items(source)]
    assert items == ["Terraform", "Kubernetes(EKS, GKE, AKS)", "Vault",
                     "Chaos Engineering", "Istio", "Python", "Go"]
    output = format_skills("Job Title: GPU Infrastructure Engineer\nGPU infrastructure with CUDA.", source, [])
    assert "Chaos Engineering" in output
    assert "Kubernetes(EKS, GKE, AKS)" in output
    assert "Technologies," not in output
    assert "Tools," not in output
