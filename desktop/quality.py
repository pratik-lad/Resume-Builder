"""Date-free rendering and transparent text-evidence checks, not an ATS predictor."""
from __future__ import annotations

import copy
import re
from html import escape
from matching import normalizer
from pipeline.output_coverage import _contains

PROJECT_DETAILS = {
    "problem": "Business Problem", "architecture": "Architecture",
    "data_flow": "Data Flow", "evaluation": "Evaluation",
    "deployment": "Deployment", "security": "Security Controls", "outcome": "Outcome",
}
ACTION = r"\b(?:built|build|implemented|implement|developed|develop|designed|design|deployed|deploy|integrated|integrate|configured|configure|orchestrated|orchestrate|evaluated|evaluate|tested|test|secured|secure|measured|measure|optimized|optimize|automated|automate|monitored|monitor|architected|architect|engineered|engineer|led|lead|maintained|maintain|established|establish|reduced|reduce)\w*\b"
MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"


def without_dates(text):
    text = re.sub(r"(?im)^\s*(?:Dates?|Period|Duration|Tenure|Employment Dates|Project Dates)\s*:\s*.*\n?", "", text)
    text = re.sub(rf"(?i)\b(?:on\s+)?(?:\d{{1,2}}\s+)?{MONTH}\s+(?:19|20)\d{{2}}(?:\s*[-–—]\s*(?:{MONTH}\s+)?(?:(?:19|20)\d{{2}}|present|current))?\b", "", text)
    text = re.sub(r"(?i)\b(?:19|20)\d{2}\s*[-–—]\s*(?:(?:19|20)\d{2}|present|current)\b", "", text)
    text = re.sub(r"\b\d{1,2}[/-]\d{1,2}[/-](?:19|20)\d{2}\b", "", text)
    text = re.sub(r"(?i)\b(?:on\s+)?(?:19|20)\d{2}[/-]\d{1,2}[/-]\d{1,2}\b", "", text)
    text = re.sub(r"(?i)\b(?:in|since|during|from|through|until|as of)\s+(?:19|20)\d{2}\b", "", text)
    text = re.sub(r"(?m)^\s*(?:19|20)\d{2}\s*$", "", text)
    def calendar_year(match):
        # A four-digit dataset count, latency or product version is not a date.
        after, before = text[match.end():], text[:match.start()]
        if re.match(r"(?i)\s*(?:documents?|records?|claims?|queries|cases?|samples?|tokens?|requests?|tests?|users?|ms|milliseconds?|seconds?)\b", after):
            return match.group()
        if re.search(r"(?i)\b(?:SQL Server|Windows Server|Visual Studio|Office)\s*$", before):
            return match.group()
        return ""
    text = re.sub(r"(?<![\w.])(?:19|20)\d{2}(?![\w.%])", calendar_year, text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def date_free_document(document):
    result = copy.deepcopy(document)
    def clean(value):
        value=without_dates(value)
        if result.get('template_version')=='reference-2':
            value=re.sub(r'(?i)\b(?:(?:in|during|throughout)\s+)?Q[1-4](?:\s+(?:19|20)\d{2})?\b', '', value)
        return value
    for section in result.get("sections", []):
        if section["key"] in {"experience", "projects"} or (result.get('date_policy') == 'all-calendars' and section['key'] != 'header'):
            section["text"] = clean(section["text"])
    for record in result.get("roles", []) + result.get("projects", []):
        for key in ("dates", "date", "period", "duration", "start_date", "end_date"):
            record.pop(key, None)
        for key, value in list(record.items()):
            if isinstance(value, str):
                record[key] = clean(value)
            elif isinstance(value, list):
                record[key] = [clean(v) if isinstance(v, str) else v for v in value]
    return result


def required_skills(req_set):
    terms = {normalizer.canonical(s) for r in req_set.requirements if r.must_have
             for s in r.canonical_skills if s}
    # Preserve named services the legacy canonical dictionary does not know.
    # A short comma-separated technology list is common in recruiter JDs.
    for req in req_set.requirements:
        if not req.must_have or req.text.count(",") < 3:
            continue
        for part in req.text.split(","):
            part = part.strip(" .;:-*")
            if not part or len(part.split()) > 7 or re.search(r"(?i)\b(?:must|required|responsible|build|develop|deliver|implement|years)\b", part):
                continue
            protected = re.sub(r"(?i)CI/CD", "CI_CD", part)
            for name in protected.split("/"):
                name = name.replace("CI_CD", "CI/CD").strip()
                if len(name) > 2:
                    terms.add(normalizer.canonical(name))
    # Requirement extraction may not identify every technology in a compound JD.
    if not terms:
        terms = normalizer.technology_terms_in_text(req_set.jd_text)
    return sorted(terms)


def contains_skill(text, skill):
    if _contains(text, skill):
        return True
    # Treat '&' and 'and' as equivalent wording, not as missing skills.
    def comparable(value):
        return re.sub(r"\s+", " ", re.sub(r"\band\b", " ", normalizer.clean(value))).strip()
    return _contains(comparable(text), comparable(skill))


def complete_skill_categories(categories, terms, jd):
    """Fill omitted required names in skills; this never creates evidence."""
    from matching import technology_catalog
    result = copy.deepcopy(categories)
    for term in terms:
        if contains_skill("\n".join(", ".join(c["items"]) for c in result), term):
            continue
        entry = technology_catalog.entry_for(term)
        name = entry["name"] if entry else (re.search(re.escape(term), jd, re.I).group() if re.search(re.escape(term), jd, re.I) else term)
        category = entry.get("category") if entry else "Additional Capabilities"
        scores = [sum((technology_catalog.entry_for(item) or {}).get("category") == category for item in c["items"]) for c in result]
        if any(scores):
            target = result[scores.index(max(scores))]
        else:
            target = next((c for c in result if c["name"] == category), None)
            if target is None:
                target = {"name": category, "items": []}
                result.append(target)
        target["items"].append(name)
    return result


def evidence_report(document, req_set):
    terms = required_skills(req_set)
    if document.get('edition')=='projects':
        from desktop.project_rules import technical_terms
        terms=technical_terms(req_set.jd_text)
    all_text = "\n".join(s["text"] for s in document["sections"])
    evidence_lines = []
    project_lines = []
    for s in document["sections"]:
        if s["key"] not in {"experience", "projects"}:
            continue
        for line in s["text"].splitlines():
            # Tools lists, section labels and category names are not evidence.
            if re.match(r"(?i)^\s*(?:Tools|Title|Client|Team Size|Operating System|Platform)\s*:", line):
                continue
            if len(line.split()) >= 12 and re.search(ACTION, line, re.I) and re.search(r"\b(?:using|via|with|through|to|by|into)\b", line, re.I):
                evidence_lines.append(line.strip().lstrip("-* "))
                if s["key"] == "projects":
                    project_lines.append(line.strip().lstrip("-* "))
    items = []
    for term in terms:
        excerpt = next((line for line in evidence_lines if contains_skill(line, term)), "")
        project_excerpt = next((line for line in project_lines if contains_skill(line, term)), "")
        items.append({"skill": term, "keyword_present": contains_skill(all_text, term),
                      "has_evidence": bool(excerpt), "excerpt": excerpt,
                      "has_project_evidence": bool(project_excerpt), "project_excerpt": project_excerpt})
    count = len(items)
    return {"required_skill_count": count,
            "keyword_coverage_percent": round(100 * sum(i["keyword_present"] for i in items) / count, 1) if count else None,
            "evidence_coverage_percent": round(100 * sum(i["has_evidence"] for i in items) / count, 1) if count else None,
            "project_evidence_coverage_percent": round(100 * sum(i["has_project_evidence"] for i in items) / count, 1) if count else None,
            "missing_project_evidence": [i["skill"] for i in items if not i["has_project_evidence"]],
            "items": items, "missing_evidence": [i["skill"] for i in items if not i["has_evidence"]]}


def evidence_html(report):
    rows = "".join(f"<tr><td>{escape(i['skill'])}</td><td>{'Present' if i['keyword_present'] else 'Missing'}</td>"
                   f"<td>{'Narrative evidence' if i['has_evidence'] else 'No narrative evidence'}</td>"
                   f"<td>{'Present' if i['has_project_evidence'] else 'Missing'}</td>"
                   f"<td>{escape(i['project_excerpt'] or i['excerpt'])}</td></tr>" for i in report["items"])
    def percentage(key):
        value = report[key]
        return f"{value}%" if value is not None else "N/A"
    return ("<h2>Required skills: keywords versus implementation evidence</h2>"
            f"<p>Keyword coverage: {percentage('keyword_coverage_percent')} | "
            f"Narrative evidence coverage: {percentage('evidence_coverage_percent')} | "
            f"Project evidence coverage: {percentage('project_evidence_coverage_percent')}</p>"
            "<p>Evidence means an action-based experience/project passage of at least twelve words mentioning the skill. "
            "This is a reproducible text check, not an ATS score or verification of fictional claims.</p>"
            "<table><tr><th>Required skill</th><th>Keyword</th><th>Evidence</th><th>Project evidence</th><th>Passage</th></tr>" + rows + "</table>")


def project_markdown(p):
    details = [label + ": " + p[key] for key, label in PROJECT_DETAILS.items() if p.get(key)]
    return "### " + p["name"] + "\n" + p["description"] + "\n\n" + "\n".join([
        "Title: " + p["role"], "Client: " + p["client"], "Platform: " + p["platform"],
        "Tools: " + p["tools"], "Team Size: " + p["team_size"], *details,
        "\nRole and Responsibilities:", "Technical:", *("- " + b for b in p["technical"]),
        "\nFunctional:", *("- " + b for b in p["functional"])])
