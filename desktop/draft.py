"""Deterministic fast draft. No model calls and no hidden network operations."""
from __future__ import annotations

import re
import time
from pathlib import Path

from matching import normalizer
from matching.experience import extract_entries
from parsers import docx_parser, pdf_parser, segmenter
from pipeline import jd, match
from schemas import Fact, Requirement, RequirementSet, SourceSpan

SECTION_TITLES = {
    "header": "Contact", "summary": "Professional Summary", "skills": "Technical Skills",
    "experience": "Professional Experience", "projects": "Selected Projects",
    "education": "Education", "certifications": "Certifications", "other": "Additional Information",
}
FACT_TYPES = {"experience": "experience_bullet", "projects": "project_bullet",
              "skills": "skill", "education": "education", "certifications": "certification",
              "summary": "summary"}


def requirements(text):
    candidates = jd._source_expectations(text)
    if not candidates:
        candidates = [(part.strip(" -*•\t"), not bool(re.search(r"preferred|nice to have|bonus", part, re.I)))
                      for part in re.split(r"\n|(?<=[.!?])\s+", text) if len(part.split()) >= 3]
    seen, items = set(), []
    for content, required in candidates:
        # Recruiter scheduling/pay metadata is not a resume qualification.
        # Standalone role titles are already represented by the headline.
        if re.match(r"(?i)^(?:shift|budget|duration|salary|compensation|location|work location|employment type|first priority|second priority)\b", content):
            continue
        if re.fullmatch(r"(?i)(?:(?:senior|junior|principal|lead)\s+)?(?:gen\s*ai|generative\s*ai|ai|ml|data|cloud|software|backend|frontend|devops|full.stack)\s+(?:lead|engineer|developer|architect|manager)", content.strip(" *")):
            continue
        original = content
        years = re.fullmatch(r"(?i)(?:experience|exp)[\s:=-]*(\d+)\s*(?:to|[-–])\s*(\d+)\s*(?:years?|yrs?)", content)
        if years:
            content = f"{years.group(1)}+ years experience"
        if content.casefold() in seen:
            continue
        seen.add(content.casefold())
        data = jd._inferred_requirement(content, required)
        data["source_text"] = original
        items.append(Requirement(req_id=f"R{len(items) + 1:02}", **data))
    return RequirementSet(extraction_version="desktop-rules-v1", requirements=items, jd_text=text)


def markdown(sections):
    blocks = []
    for item in sections:
        body = item["text"].strip()
        if item["key"] in {"experience", "projects"}:
            from desktop.quality import without_dates
            body = without_dates(body)
        if item["key"] == "projects" and item["title"] == "Relevant Project Experience":
            from desktop.project_document import mask_text
            body = mask_text(body, company_label=bool(re.search(r'(?im)^Company name:', body)))
        if not body:
            continue
        blocks.append(body if item["key"] == "header" else f"## {item['title']}\n{body}")
    return "\n\n".join(blocks)


def generate(payload, progress):
    started = time.perf_counter()
    path = Path(payload["resume"])
    suffix = path.suffix.lower()
    if suffix not in {".pdf", ".docx"}:
        raise ValueError("Choose a PDF or DOCX resume. Legacy .doc files must be saved as DOCX.")
    if path.stat().st_size > 25 * 1024 * 1024:
        raise ValueError("The resume file exceeds 25 MB. Please use a smaller document.")
    text = payload["jd"].strip()
    if not text:
        raise ValueError("Paste a job description first.")
    if len(text) > 100_000:
        raise ValueError("Job description exceeds 100,000 characters.")
    progress("parse", "Reading resume")
    doc = pdf_parser.parse_pdf(str(path)) if suffix == ".pdf" else docx_parser.parse_docx(str(path))
    if not doc.raw_text.strip() or (suffix == ".pdf" and doc.is_degenerate()):
        raise ValueError("This PDF has too little readable text or is scanned. Use a text PDF or DOCX; OCR is not included.")
    progress("match", "Matching source experience to job requirements")
    req_set = requirements(text)
    source_sections = segmenter.segment(doc)
    facts, sections, entries = [], [], []
    for section in source_sections:
        key = section.name if section.name in SECTION_TITLES else "other"
        body = "\n".join(line.text for line in section.lines) if key == "header" else section.text
        # Skills may be ranked independently; keep employment/project blocks
        # intact so employers, dates and their bullets cannot be mixed.
        if key == "skills":
            rows = body.splitlines()
            wanted = normalizer.technology_terms_in_text(text)
            rows.sort(key=lambda row: -len(normalizer.technology_terms_in_text(row) & wanted))
            body = "\n".join(rows)
        sections.append({"key": key, "title": SECTION_TITLES[key], "text": body})
        if key == "experience":
            entries.extend(extract_entries(section.text))
        if key == "header":
            continue
        for line in section.lines:
            if not line.text.strip():
                continue
            facts.append(Fact(fact_id=f"F{len(facts) + 1:03}", type=FACT_TYPES.get(key, "other"),
                              text=line.text.strip(), section_heading=key,
                              entities={"tech": sorted(normalizer.technology_terms_in_text(line.text))},
                              source=SourceSpan(page=line.page, char_start=line.char_start, char_end=line.char_end)))
    if not facts:
        # Plain unheaded resumes remain lossless and editable.
        facts = [Fact(fact_id="F001", type="other", text=doc.raw_text)]
    from desktop.embedding import install
    install()
    matches, card, gap = match.run(req_set, facts, doc.raw_text, entries)
    # Rank SECTION blocks, never individual lines of employment records.
    scores = {f.fact_id: m.score for m in matches for f in facts if f.fact_id in m.fact_ids}
    relevance = {key: max((scores.get(f.fact_id, 0) for f in facts if f.section_heading == key), default=0)
                 for key in SECTION_TITLES}
    order = {"header": 0, "summary": 1, "skills": 2, "experience": 3, "projects": 3,
             "education": 4, "certifications": 5, "other": 6}
    sections.sort(key=lambda s: (order[s["key"]], -relevance[s["key"]]))
    mode = payload.get("mode", "demo")
    if mode == "demo":
        # Preserve fabrication as an explicit capability. This path intentionally
        # bypasses source-claim rejection, just like the existing demo workflow.
        technologies = sorted(normalizer.technology_terms_in_text(text))
        skill_text = ", ".join(technologies)
        skills = next((s for s in sections if s["key"] == "skills"), None)
        if not skills:
            skills = {"key": "skills", "title": SECTION_TITLES["skills"], "text": ""}
            sections.insert(2 if len(sections) > 1 else 1, skills)
        if skill_text:
            skills["text"] += "\n- Additional capabilities: " + skill_text
        projects = next((s for s in sections if s["key"] == "projects"), None)
        if projects is None:
            projects = {"key": "projects", "title": SECTION_TITLES["projects"], "text": ""}
            at = next((i for i, s in enumerate(sections) if s["key"] == "education"), len(sections))
            sections.insert(at, projects)
        tools = skill_text or "automated testing, monitoring, and deployment"
        for title, purpose in (("Delivery Operations Platform", "reliable release delivery"),
                               ("Service Insights Hub", "operational reporting and incident analysis")):
            projects["text"] += (
                f"\n\n### {title}\nTools: {tools}\n"
                f"- Designed a platform for {purpose}, integrating {tools}.\n"
                "- Built ingestion, validation, and reporting components with automated tests.\n"
                "- Established monitoring, deployment checks, and recovery procedures.\n"
                "- Reduced manual processing by 30% through repeatable workflows."
            )
        certificates = next((s for s in sections if s["key"] == "certifications"), None)
        if certificates is None:
            certificates = {"key": "certifications", "title": SECTION_TITLES["certifications"], "text": ""}
            sections.append(certificates)
        for technology in technologies[:2]:
            certificates["text"] += f"\n- Advanced Professional Certification in {technology}"
    result = {
        "sections": sections, "source": doc.raw_text, "jd": text, "mode": mode,
        "requirements": req_set.model_dump(), "source_score": card.model_dump(),
        "source_matches": [m.model_dump() for m in matches], "source_gap": gap.model_dump(),
        "facts": [f.model_dump() for f in facts],
        "warnings": doc.warnings, "draft_seconds": round(time.perf_counter() - started, 3),
    }
    progress("ready", "Draft ready")
    return result


def export(payload, progress):
    from pipeline import render
    from desktop.bootstrap import DATA
    from html import escape
    import uuid
    from desktop.quality import date_free_document, evidence_report, evidence_html
    from desktop.project_document import sanitize
    document = sanitize(payload["document"])
    content = markdown(document["sections"])
    req_set = requirements(document["jd"]) if "jd" in document else RequirementSet(**document["requirements"])
    kind = payload["kind"]
    progress("export", "Building export from your current edits")
    staging = DATA / "artifacts" / (uuid.uuid4().hex + (".docx" if kind == "docx" else ".html"))
    if kind == "docx":
        from docgen.reference_template import PROJECT_FIELDS
        from desktop.quality import PROJECT_DETAILS
        PROJECT_FIELDS.update(label.casefold() for label in PROJECT_DETAILS.values())
        PROJECT_FIELDS.add("platform")
        if document.get('profile_version'):
            PROJECT_FIELDS.update({'target role', 'contribution'})
        if document.get("template_version") == "reference-2":
            from desktop.reference_layout import docx
            docx(document, staging)
        else:
            render.build_ideal_docx(content, staging)
    elif kind == "html":
        if document.get('edition')=='projects':
            from desktop.project_document import report_shell
            html=report_shell(document)
        else:
            html = render.build_ideal_report(content, req_set)
        html = html.replace("</body>", evidence_html(evidence_report(document, req_set)) + "</body>")
        if document.get("edition") == "projects":
            from desktop.project_rules import report, report_html
            html = html.replace("</body>", report_html(report(document)) + "</body>")
        if document.get('ledger_version'):
            from desktop.requirement_ledger import report as ledger_report, html as ledger_html
            html = html.replace('</body>', ledger_html(ledger_report(document)) + '</body>')
        warnings=document.get('warnings',[])
        if document.get('profile_version'):
            # Intermediate drafts stored profile findings in general warnings.
            # Profile findings are recalculated above from the current edits.
            profile_prefixes=('Summary ', 'Professional summary ', 'Repeated professional-summary ',
                              'Keep quantified project ', 'Summarize the career strength ')
            warnings=[w for w in warnings if not str(w).startswith(profile_prefixes)]
        if warnings:
            notes = "<h2>Review notes</h2><ul>" + "".join("<li>" + escape(str(note)) + "</li>" for note in warnings) + "</ul>"
            html = html.replace("</body>", notes + "</body>")
        label = "Fictional/demo: may contain invented experience and claims." if document["mode"] == "demo" else "Source-based draft; review any manual edits."
        staging.write_text(html.replace("<body>", f"<body><p><strong>{escape(label)}</strong></p>", 1), encoding="utf-8")
    else:
        raise ValueError("Unknown export type.")
    return {"artifact": str(staging), "destination": payload["destination"]}
