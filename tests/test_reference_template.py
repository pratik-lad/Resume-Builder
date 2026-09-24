import sys
from pathlib import Path

from docx import Document
from docx.oxml.ns import qn

sys.path.insert(0, str(Path(__file__).parents[1] / "api"))
from pipeline.render import build_ideal_docx


def test_reference_design_and_tables_preserve_content(tmp_path):
    markdown = """# Example Candidate
Senior DevOps Engineer
## Summary
- Built **cloud infrastructure**.
## Technical Skills
- **Cloud:** Azure, AWS
- **Languages:** Python, Go
## Education
| Degree | Institute | CGPA |
| --- | --- | --- |
| BTech | Example College | 7.9 |
## Relevant Project Experience
### Platform Modernization
**Client:** Enterprise
**Tools:** Kubernetes, Terraform
**Team size:** 10
**Project Description:** Cloud delivery platform
#### Technical
- Automated deployments.
## Certifications
- Azure Fundamentals
"""
    doc = Document(build_ideal_docx(markdown, tmp_path / "resume.docx"))
    assert len(doc.tables) == 1
    text = "\n".join(p.text for p in doc.paragraphs) + "\n" + "\n".join(
        cell.text for t in doc.tables for row in t.rows for cell in row.cells)
    for expected in ("Example Candidate", "Azure, AWS", "Example College", "7.9",
                     "Enterprise", "10", "Cloud delivery platform", "Automated deployments."):
        assert expected in text
    assert doc.styles["Normal"].font.name == "Calibri"
    assert doc.sections[0]._sectPr.find(qn("w:pgBorders")) is None
    assert 'PAGE' in doc.sections[0].footer._element.xml
    assert 'CBD8DF' in doc._element.xml
    assert doc.tables[0].rows[0]._tr.find('.//' + qn('w:tblHeader')) is not None


def test_unstructured_education_and_unknown_sections_remain_visible(tmp_path):
    doc = Document(build_ideal_docx(
        "# Candidate\n## Education\nPhD in Computing\n## Research Interests\nDistributed systems",
        tmp_path / "resume.docx"))
    assert "PhD in Computing" in [p.text for p in doc.paragraphs]
    assert "Distributed systems" in [p.text for p in doc.paragraphs]
