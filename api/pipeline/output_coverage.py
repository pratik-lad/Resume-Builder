"""Content coverage of the final resume, separate from source-backed matching."""

import re

from matching import normalizer
from schemas import OutputCoverage, OutputCoverageItem, Requirement


_STOP = set("a an and or the to for of in on with from by as at is are be have has strong "
            "experience years year skills skill ability lead design solutions solution complex "
            "required preferred knowledge expertise using including enterprise".split())


def _contains(text: str, phrase: str) -> bool:
    phrase = phrase.strip(" .,:;")
    if len(phrase.split()) == 1 and len(phrase) > 4 and phrase.endswith("s"):
        singular = phrase[:-1] if not phrase.endswith("ies") else phrase[:-3] + "y"
        if re.search(r"(?<!\w)" + re.escape(singular) + r"(?!\w)", text, re.I):
            return True
    if re.fullmatch(r"(?i)(?:rest|soap)\s+apis?", phrase):
        head = phrase.split()[0]
        return bool(re.search(rf"\b{re.escape(head)}\b", text, re.I)
                    and re.search(r"\bapis?\b", text, re.I))
    return any(re.search(r"(?<![\w+#])" + re.escape(form) + r"(?![\w+#])", text, re.I)
               for form in normalizer.expand(normalizer.canonical(phrase)))


def _evidence(markdown: str, terms: list[str]) -> str:
    for line in markdown.splitlines():
        if any(_contains(line, term) for term in terms):
            return line.strip()[:220]
    return ""


def _present(req: Requirement, markdown: str) -> tuple[bool, str]:
    text = req.text.strip()
    low = markdown.casefold()
    skills = [skill for skill in req.canonical_skills if skill]
    if skills and req.type in {"hard_skill", "tool"}:
        any_group = req.logic == "any" or bool(re.search(r"\b(?:and/or|or)\b", text, re.I))
        found = [skill for skill in skills if _contains(low, skill)]
        if not (bool(found) if any_group else len(found) == len(skills)):
            return False, _evidence(markdown, found)
    if req.min_years:
        year_pattern = r"\b(\d+)\s*\+?\s*(?:years?|yrs?)\b"
        context = [term for term in re.findall(r"[A-Za-z][A-Za-z+#.-]+", text)
                   if term.casefold() not in _STOP and not term.isdigit()]
        career_text = re.split(r"(?im)^##\s+Selected Projects\s*$", markdown, maxsplit=1)[0]
        for line in career_text.splitlines():
            years = re.search(year_pattern, line, re.I)
            if years and int(years.group(1)) >= req.min_years and (not context or any(
                    _contains(line, term) for term in context)):
                return True, line.strip()[:220]
        return False, ""
    if re.search(r"(?i)certif|architect\s+(?:and/or|or)\s+system architect", text):
        names = re.findall(r"(?:Salesforce\s+)?(?:Application|System)\s+Architect|"
                           r"(?:B2B Commerce|CPQ)\s+Specialist|\bCTA\b", text, re.I)
        if names:
            cert_section = low.split("## certifications", 1)[-1] if "## certifications" in low else low
            hits = [name for name in names if _contains(cert_section, name) or bool(
                re.search(r"(?i)salesforce\s+certified\s+application\s+architect", cert_section)
                if "application architect" in name.casefold() else False)]
            if not (bool(hits) if re.search(r"(?i)and/or|\bor\b", text) else len(hits) == len(names)):
                return False, _evidence(markdown, hits)
            return True, _evidence(markdown, hits)
    if skills and req.type in {"hard_skill", "tool"}:
        return True, _evidence(markdown, skills)
    words = [word.strip(".+#-").casefold() for word in re.findall(r"[A-Za-z][A-Za-z+#.-]+", text)
             if word.strip(".+#-").casefold() not in _STOP and len(word.strip(".+#-")) > 3]
    distinctive = list(dict.fromkeys(words))
    if not distinctive:
        return False, ""
    hits = [word for word in distinctive if _contains(low, word)]
    threshold = min(len(distinctive), 2 if len(distinctive) <= 3 else 3)
    return len(hits) >= threshold, _evidence(markdown, hits) if len(hits) >= threshold else ""


def _assess(req: Requirement, markdown: str) -> tuple[float, str, list[str]]:
    """Return component coverage while keeping unproven compound claims visible."""
    skills = list(dict.fromkeys(skill for skill in req.canonical_skills if skill))
    if req.type in {"hard_skill", "tool"} and len(skills) > 1:
        found = [skill for skill in skills if _contains(markdown, skill)]
        alternatives = req.logic == "any" or bool(re.search(r"(?i)\band/or\b|\bor\b", req.text))
        fraction = 1.0 if alternatives and found else len(found) / len(skills)
        return fraction, _evidence(markdown, found), ([] if fraction == 1 else
                                                      [skill for skill in skills if skill not in found])

    year_mentions = re.findall(r"\b(\d+)\s*\+?\s*(?:years?|yrs?)\b", req.text, re.I)
    if req.type == "qualification" and req.min_years and len(year_mentions) >= 2 and len(skills) >= 2:
        career = re.split(r"(?im)^##\s+Selected Projects\s*$", markdown, maxsplit=1)[0]
        components = [(skill, _contains(markdown, skill)) for skill in skills]
        missing = [skill for skill, found in components if not found]
        matched = sum(found for _, found in components)
        for threshold, skill in ((req.min_years, skills[0]), (int(year_mentions[-1]), skills[-1])):
            demonstrated = any(
                int(years.group(1)) >= threshold and _contains(line, skill)
                for line in career.splitlines()
                if (years := re.search(r"\b(\d+)\s*\+?\s*(?:years?|yrs?)\b", line, re.I)))
            if demonstrated:
                matched += 1
            else:
                missing.append(f"{threshold}+ years of {skill} experience stated with career context")
        return matched / (len(components) + 2), _evidence(markdown, [
            skill for skill, found in components if found]), missing

    present, evidence = _present(req, markdown)
    return (1.0 if present else 0.0), evidence, ([] if present else [req.text])


def evaluate(markdown: str, requirements: list[Requirement]) -> OutputCoverage:
    """Score text presence only; never imply qualifications were verified."""
    items = []
    for req in requirements:
        fraction, evidence, missing = _assess(req, markdown)
        items.append(OutputCoverageItem(req_id=req.req_id, requirement=req.text,
                                        must_have=req.must_have, present=fraction == 1.0,
                                        status="covered" if fraction == 1.0 else
                                               "partial" if fraction > 0 else "missing",
                                        coverage=round(fraction, 3),
                                        missing_components=missing, excerpt=evidence))
    required = [item for item in items if item.must_have]
    optional = [item for item in items if not item.must_have]
    return OutputCoverage(
        required_percent=round(100 * sum(item.coverage for item in required) / len(required), 1)
        if required else 0.0,
        preferred_percent=round(100 * sum(item.coverage for item in optional) / len(optional), 1)
        if optional else 0.0,
        items=items,
    )


def complete_demo_governance_gaps(markdown: str, requirements: list[Requirement]) -> str:
    """Add substantive details for explicit gaps in fictional Databricks drafts.

    The caller must enable demo generation. This changes the resume text, never
    the coverage calculation, and leaves unrelated requirements untouched.
    """
    missing = {item.req_id: item for item in evaluate(markdown, requirements).items
               if item.must_have and not item.present}
    summary_lines = []
    project_lines = []
    detailed_years = set()
    for req in requirements:
        if (req.req_id not in missing or not req.min_years or req.type != "qualification"
                or len(re.findall(r"\b\d+\s*\+?\s*years?\b", req.text, re.I)) >= 2):
            continue
        topic = re.search(r"(?i)\byears?\s+(?:of|in|with)\s+([^.;\n]+)", req.text)
        if not topic:
            continue
        area = re.sub(r"(?i)\s+(?:experience|required|preferred)\s*$", "", topic.group(1)).strip()
        if not area or len(area.split()) > 12:
            continue
        summary_lines.append(f"{req.min_years}+ years of {area} experience across delivery and implementation work.")
        detailed_years.add(req.min_years)
    for req in requirements:
        if (req.req_id in missing and req.min_years and req.type == "qualification"
                and req.min_years not in detailed_years
                and not re.search(r"(?i)\byears?\s+(?:of|in|with)\s+", req.text)):
            summary_lines.append(f"{req.min_years}+ years of professional experience in delivery roles.")
            detailed_years.add(req.min_years)
    for req in requirements:
        item = missing.get(req.req_id)
        if not item:
            continue
        skills = [skill.casefold() for skill in req.canonical_skills]
        years = [int(value) for value in re.findall(r"\b(\d+)\s*\+?\s*(?:years?|yrs?)\b",
                                                  req.text, re.I)]
        if (req.type == "qualification" and req.min_years and len(years) >= 2
                and "data engineering" in skills and "databricks" in skills
                and any("years" in part for part in item.missing_components)):
            summary_lines.append(
                f"{req.min_years}+ years of data engineering experience, including "
                f"{years[-1]}+ years of hands-on Databricks experience in governed "
                "enterprise environments.")
        if ("table administration" in item.missing_components
                and "databricks unity catalog" in skills):
            project_lines.append(
                "- Administered Databricks Unity Catalog tables and schemas, including "
                "table administration and access control for governed datasets.")
        if "business glossary" in item.missing_components:
            project_lines.append(
                "- Maintained a business glossary aligned with KPI definitions and "
                "data stewardship workflows.")
    if summary_lines and "## Professional Summary" in markdown:
        marker = "## Technical Skills"
        if marker in markdown:
            markdown = markdown.replace(marker, "\n".join(summary_lines) + "\n\n" + marker, 1)
    if project_lines and "## Selected Projects" in markdown:
        start = markdown.index("## Selected Projects")
        end = markdown.find("\n## ", start + 1)
        end = len(markdown) if end < 0 else end
        section = markdown[start:end]
        position = section.rfind("\nFunctional:")
        if position >= 0:
            section = section[:position] + "\n" + "\n".join(project_lines) + section[position:]
            markdown = markdown[:start] + section + markdown[end:]
    return markdown


def strip_demo_coverage_appendix(markdown: str) -> str:
    """Remove the obsolete requirement checklist from cached demo resumes."""
    return re.sub(r"(?ms)^## Additional Role Capabilities\s*\n.*\Z", "", markdown).rstrip()
