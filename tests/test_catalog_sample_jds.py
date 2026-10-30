"""Fresh sample-JD checks; no dependency on the old 17-case manifest."""

import re
import sys
from pathlib import Path

import pytest
from docx import Document

ROOT = next((parent for parent in Path(__file__).resolve().parents
             if (parent / "Sample JD" / "all in one.docx").exists()),
            Path(__file__).resolve().parents[1])
SAMPLE_JDS = ROOT / "Sample JD" / "all in one.docx"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from matching.technology_catalog import context_for_jd  # noqa: E402
from pipeline.skill_layout import format_skills  # noqa: E402


@pytest.mark.skipif(not SAMPLE_JDS.exists(), reason="local sample JD document unavailable")
def test_current_sample_jds_use_relevant_terms_without_losing_source_skills():
    paragraphs = [p.text for p in Document(SAMPLE_JDS).paragraphs]
    headings = [i for i, value in enumerate(paragraphs) if re.match(r"^JD \d+\b", value)]

    def job(number: int) -> str:
        start = next(i for i in headings if re.match(rf"^JD {number}\b", paragraphs[i]))
        end = next((i for i in headings if i > start), len(paragraphs))
        return "\n".join(paragraphs[start:end])

    source = "Candidate\nSKILLS\nPython, Terraform\nEDUCATION\nDegree"
    lakehouse = job(8)
    salesforce = job(14)
    assert "Delta Lake" in context_for_jd(lakehouse)
    assert "Salesforce CPQ" in context_for_jd(salesforce)
    for jd in (lakehouse, salesforce):
        skills = format_skills(jd, source, [])
        assert "Python" in skills and "Terraform" in skills
        assert all(line.startswith("- **") for line in skills.splitlines())
