"""Build and tailor a candidate resume to the complete job description."""

import re
from difflib import SequenceMatcher
import calendar
from datetime import date
from typing import Iterable

from config import settings
from llm.client import chat
from matching import normalizer
from pipeline.skill_layout import format_skills
from pipeline.practical_detail import strongest_bullets
from matching.technology_catalog import context_for_jd
from schemas import ExperienceEntry


PROMPT_VERSION = "resume-builder-tailoring-v18"
FINALIZER_VERSION = "resume-finalizer-v37"

_DISPLAY_SKILL = {
    "nodejs": "Node.js", "express": "Express.js", "websockets": "WebSockets",
    "mongodb": "MongoDB", "react": "ReactJS", "nextjs": "Next.js",
    "redux": "Redux", "nestjs": "Nest.js", "socketio": "Socket.io",
    "rest api": "REST APIs", "javascript": "JavaScript",
}

_GENERIC_REQUIREMENT_TERMS = {"behavior", "cleanup", "configuration", "limitations"}
_PLACEHOLDER_CLAIM = re.compile(
    r"(?i)\b(?:address (?:ai agent )?ownership|add jd-aligned|please update|"
    r"add responsibilities|specific project name|distinct part of the target role)\b|"
    r"\[(?:update|add|insert|mm/yyyy|candidate|company)[^\]]*\]"
)


def _practical_detail_placeholder(line: str) -> bool:
    return bool(_PLACEHOLDER_CLAIM.search(line))


def _display_required_skill(skill: str) -> str:
    if skill in _DISPLAY_SKILL:
        return _DISPLAY_SKILL[skill]
    words = skill.split()
    acronyms = {"gpu", "gpus", "llm", "ml", "nvml", "dcgm", "bmc", "ipmi", "gemm", "nccl", "api"}
    return " ".join(word.upper() if word in acronyms else word.capitalize() for word in words)


def _skill_in_section(skill: str, section: str) -> bool:
    normalized = lambda value: re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()
    phrase = normalized(skill)
    return bool(phrase and re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])",
                                     normalized(section)))


def _additional_skill_lines(skills: list[str]) -> list[str]:
    groups = {"GPU & Workloads": [], "Telemetry & Data Quality": [],
              "Platform Operations": []}
    for skill in skills:
        key = skill.casefold()
        if any(word in key for word in ("gpu", "model", "workload", "edge", "determinism", "reproducib")):
            group = "GPU & Workloads"
        elif any(word in key for word in ("telemetry", "data", "sensor", "sampling", "timestamp", "clock", "time series")):
            group = "Telemetry & Data Quality"
        else:
            group = "Platform Operations"
        groups[group].append(skill)
    return [f"- Additional {name}: " + ", ".join(items)
            for name, items in groups.items() if items]


def _required_jd_skill_terms(jd_text: str) -> set[str]:
    """Include unfamiliar tools explicitly named in required-skill language."""
    terms = normalizer.technology_terms_in_text(jd_text)
    cue = re.compile(r"\b(?:knowledge|proficiency|expertise|familiarity|experience)\s+"
                     r"(?:in|of|with)\s+([^.;\n]{1,160})", re.I)
    for match in cue.finditer(jd_text):
        for part in re.split(r",|\band\b|\bor\b", match.group(1), flags=re.I):
            candidate = part.strip(" .:()[]")
            if (candidate and len(candidate.split()) <= 4
                    and re.search(r"[A-Z0-9.#/+]|^[a-z][a-z0-9+#.-]{2,}$", candidate)):
                terms.add(normalizer.canonical(candidate))
    required_section = False
    for line in jd_text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^required (?:technical )?skills(?:\s*(?:&|and)\s*experience)?\s*:?$", stripped):
            required_section = True
            continue
        if required_section and (not stripped or re.match(
                r"(?i)^(?:preferred|nice to have|candidate profile|responsibilities|about the role)\b", stripped)):
            required_section = False
        if required_section and re.match(r"^[-*•]\s+[^.;:]{2,50}$", stripped):
            terms.add(normalizer.canonical(re.sub(r"^[-*•]\s+", "", stripped)))
    return terms

_SECTION_ALIASES = {
    "profile summary": "professional summary",
    "summary": "professional summary",
    "professional summary": "professional summary",
    "skills": "technical skills",
    "technical skills": "technical skills",
    "projects": "selected projects",
    "project experience": "selected projects",
    "new project": "selected projects",
    "new jd-aligned project": "selected projects",
    "selected projects": "selected projects",
    "education": "education",
}


def _section_positions(markdown: str) -> dict[str, int]:
    """Return normalized H2 section positions without depending on one exact title."""
    positions: dict[str, int] = {}
    for match in re.finditer(r"(?im)^##\s+(.+?)\s*$", markdown):
        section = _SECTION_ALIASES.get(match.group(1).strip().casefold())
        if section and section not in positions:
            positions[section] = match.start()
    return positions


def _strip_repair_artifacts(markdown: str) -> str:
    """Remove internal repair diagnostics that are never valid resume content."""
    marker = re.compile(
        r"(?im)^[ \t]*(?:#{1,6}[ \t]*)?(?:\*\*)?[ \t]*(?:"
        r"rebuild and tailor this candidate resume to the complete job description\b|"
        r"missing jd skills[ \t]*:|missing sections[ \t]*:|"
        r"new project misplaced or missing[ \t]*:|"
        r"return a complete replacement resume\b|"
        r"return only the completed resume\b|"
        r"the new project is missing, so i added it\b)"
    )
    match = marker.search(markdown)
    return markdown[:match.start()].rstrip() if match else markdown


def clean_export_markdown(markdown: str) -> str:
    """Remove repair echoes and regroup source activities for saved-run exports."""
    markdown = _strip_repair_artifacts(markdown)
    other = re.search(
        r"(?ims)^##[ \t]+Other Skills and Interests[ \t]*\n(.*?)(?=^##[ \t]+|\Z)",
        markdown,
    )
    if not other:
        return markdown
    activities, achievements = [], []
    for line in other.group(1).splitlines():
        if re.match(r"^[ \t]*[-*+•][ \t]+", line):
            (achievements if re.match(
                r"^[ \t]*[-*+•][ \t]+(?:achieved|awarded|winner|runner-up|shortlisted|recognized)\b",
                line, re.I) else activities).append(line.strip())
        elif line.strip():
            activities.append(line.strip())
    replacement = "\n\n".join(
        f"## {title}\n" + "\n".join(lines)
        for title, lines in (("Extracurricular Activities", activities),
                             ("Achievements", achievements)) if lines
    )
    return (markdown[:other.start()] + replacement + markdown[other.end():]).strip()


def _experience_month(value: str, today: date) -> tuple[int, int] | None:
    value = value.strip().casefold().replace(".", "")
    if value in {"present", "current", "now"}:
        return today.year, today.month
    numeric = re.fullmatch(r"(\d{1,2})[/-](\d{4})", value)
    if numeric:
        month, year = map(int, numeric.groups())
        return (year, month) if 1 <= month <= 12 else None
    months = {name.casefold(): number for number, name in enumerate(calendar.month_abbr) if name}
    months.update({name.casefold(): number for number, name in enumerate(calendar.month_name) if name})
    named = re.fullmatch(r"([a-z]+)\s+(\d{4})", value)
    if named and named.group(1) in months:
        return int(named.group(2)), months[named.group(1)]
    return (int(value), 1) if re.fullmatch(r"\d{4}", value) else None


def _total_experience_label(entries: Iterable[ExperienceEntry]) -> str | None:
    """Calculate non-overlapping professional months from explicit source dates."""
    today = date.today()
    intervals = []
    for entry in entries:
        start = _experience_month(entry.start_date, today)
        end = _experience_month("present" if entry.current else entry.end_date, today)
        if not start or not end:
            continue
        start_index, end_index = start[0] * 12 + start[1], end[0] * 12 + end[1]
        if end_index > start_index:
            intervals.append((start_index, end_index))
    if not intervals:
        return None
    intervals.sort()
    merged = []
    for start, end in intervals:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    months = sum(end - start for start, end in merged)
    years, remainder = divmod(months, 12)
    return f"{years} Year{'s' if years != 1 else ''}" + (f" {remainder} Month{'s' if remainder != 1 else ''}" if remainder else "")


def _source_experience_section(entries: list[ExperienceEntry]) -> str:
    """Render source-backed employment identities and dates, never model-invented employers."""
    duration = _total_experience_label(entries)
    lines = [f"Total Professional Experience: {duration}"] if duration else []
    for entry in entries:
        identity = " | ".join(part for part in (entry.role_title, entry.company) if part)
        if not identity:
            identity = "Professional Experience"
        dates = " – ".join(part for part in (entry.start_date, entry.end_date or ("Present" if entry.current else "")) if part)
        lines.extend([f"### {identity}", dates or "Dates: Please update with your actual employment dates"])
        detail = entry.source_evidence.strip()
        if detail:
            lines.append(f"- {detail}")
    return "\n".join(line for line in lines if line.strip())


def _tailored_experience_section(entries: list[ExperienceEntry], generated_body: str,
                                 required_responsibilities: Iterable[str] = ()) -> str:
    """Keep source job identities while retaining Dolphin's tailored experience bullets."""
    bullets = [line.strip() for line in generated_body.splitlines()
               if re.match(r"^\s*[-*]\s+\S", line)]
    rendered = "\n".join(bullets).casefold()
    for responsibility in required_responsibilities:
        normalized = re.sub(r"\W+", " ", responsibility).strip().casefold()
        if normalized and normalized not in re.sub(r"\W+", " ", rendered):
            bullets.append(f"- {responsibility.rstrip('.') }.")
            rendered += "\n" + normalized
    lines = ["Total Professional Experience: [Update from actual employment dates]"]
    for index, entry in enumerate(entries):
        identity = " | ".join(part for part in (entry.role_title, entry.company) if part)
        if not identity:
            identity = "Professional Experience"
        lines.extend([f"### {identity}", "Dates: [MM/YYYY - MM/YYYY or Present]"])
        assigned = bullets[index::len(entries)]
        if assigned:
            lines.extend(assigned)
        else:
            lines.append("- [Add JD-aligned responsibilities for this role]")
    return "\n".join(line for line in lines if line.strip())


def _project_blocks(markdown: str) -> list[tuple[str, str]]:
    """Return project headings and bodies in order without interpreting them as fabricated jobs."""
    return re.findall(r"(?ms)^###\s+(.+?)\s*$\n(.*?)(?=^###\s+|\Z)", markdown)


def _project_relevance(block: tuple[str, str], jd_text: str) -> int:
    """Rank additional projects by distinct JD vocabulary, not model position."""
    jd_terms = {term for term in re.findall(r"[a-z][a-z0-9+#.-]{3,}", jd_text.casefold())
                if term not in {"experience", "preferred", "required", "candidate", "strong",
                                "years", "architect", "technical", "solutions", "design"}}
    content = " ".join(block).casefold()
    return sum(bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", content)) for term in jd_terms)


def _resume_project_heading(heading: str, target_role: str) -> str:
    """Remove internal planning labels from an appended project's visible title."""
    heading = re.sub(r"^(?:existing\s+project\s+name|project\s+name)\s*:?\s*", "", heading, flags=re.I)
    clean = re.sub(r"\b(?:new|jd[ -]?aligned|target(?:ed)?\s+solution|fictional|demo|synthetic|sample|placeholder)\b",
                   "", heading, flags=re.I)
    clean = re.sub(r"^\s*[:|\-]+\s*", "", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    if clean.casefold() in {"", "project", "delivery platform"}:
        role = re.sub(r"\b(?:target|role)\b", "", target_role, flags=re.I).strip() or "Product"
        return f"{role} Delivery Platform"
    return clean


def _copied_jd_duty(bullet: str, jd_text: str) -> bool:
    """Identify bullets that reproduce a JD line instead of describing work."""
    def normalize(value: str) -> str:
        return " ".join(re.findall(r"[a-z0-9+#.]+", value.casefold()))

    candidate = normalize(re.sub(r"^\s*[-*]\s+", "", bullet))
    if len(candidate.split()) < 6:
        return False
    for line in jd_text.splitlines():
        for sentence in re.split(r"(?<=[.!?])\s+|\s*;\s*", line):
            source = normalize(re.sub(r"^\s*[-*#>]+\s*", "", sentence))
            if len(source.split()) >= 6 and SequenceMatcher(None, candidate, source).ratio() >= 0.9:
                return True
    return False


def _target_role(jd_text: str) -> str:
    explicit = re.search(r"(?im)^\s*#{0,6}\s*\*{0,2}\s*Job Title\s*:\s*([^\r\n*#]+)", jd_text)
    if explicit:
        return explicit.group(1).strip()
    url_title = re.search(r"(?i)#\s*Job Title\s*:\s*([^\r\n*#]+)", jd_text)
    if url_title:
        return url_title.group(1).strip()
    first_line = next((line.strip(" *\t") for line in jd_text.splitlines() if line.strip()), "")
    if len(first_line) <= 80 and re.search(r"\b(?:engineer|developer|analyst|manager|designer|scientist|architect)\b",
                                        first_line, re.I) and ":" not in first_line \
            and not re.match(r"^(?:as|for)\b", first_line, re.I) and " at " not in first_line.casefold():
        return first_line
    match = re.search(r"(?im)^\s*\*{0,2}Job Title:\s*([^\r\n*]+)", jd_text)
    if match:
        return match.group(1).strip()
    match = re.search(
        r"\b(?:as|for)\s+(?:an?\s+)?([A-Z][A-Za-z &.+/-]{2,70}?(?:Developer|Engineer|Scientist|Analyst|Manager|Designer))\b",
        jd_text, re.I)
    if match:
        return match.group(1).strip()
    if (re.search(r"(?i)artificial intelligence|\bAI\b", jd_text)
            and re.search(r"(?i)design, develop, test, deploy|MLOps|AI agent", jd_text)):
        return "AI Engineer"
    if re.search(r"(?i)machine learning", jd_text) and re.search(r"(?i)design|develop|deploy", jd_text):
        return "Machine Learning Engineer"
    if re.search(r"(?i)\b(?:LLM|RAG|MLOps|Copilot Studio|Azure AI)\b", jd_text):
        return "AI Engineer"
    if re.search(r"(?i)\b(?:Power BI|Tableau|business intelligence|data analyst)\b", jd_text):
        return "Data Analyst"
    if re.search(r"(?i)\b(?:data pipeline|data warehouse|ETL|data engineering)\b", jd_text):
        return "Data Engineer"
    if re.search(r"(?i)\b(?:sales|business development|account growth)\b", jd_text):
        return "Business Development Manager"
    return "Software Engineer"


def _source_entries(resume_text: str) -> list[ExperienceEntry]:
    """Recover role headers from text PDFs when structured employment extraction is empty."""
    entries = []
    headers = list(re.finditer(r"(?m)^#?([^\n:]{3,90})\s*\(([^)\n]{6,65})\):?\s*$", resume_text))
    for index, match in enumerate(headers, 1):
        company, dates = (value.strip() for value in match.groups())
        context = resume_text[match.end():headers[index].start() if index < len(headers)
                              else len(resume_text)]
        role = re.search(r"(?im)^Designation:\s*([^\n]+)", "\n".join(context.splitlines()[:6]))
        if role and re.search(r"\d{4}", dates):
            entries.append(ExperienceEntry(
                entry_id=f"EXP-TEXT-{index:02d}", company=company, role_title=role.group(1).strip(),
                start_date=dates, source_evidence=match.group(0).strip()))
    known_titles = {entry.role_title.casefold() for entry in entries}
    # Date removal leaves explicit role headers intact in anonymized resumes.
    # The employer marker may be followed by an employer tagline on the same
    # line after PDF text extraction; keep that context out of both identity
    # fields and preserve the visible #Confidential source label.
    for index, line in enumerate(resume_text.splitlines(), 1):
        match = re.match(r"^([^|]{3,90}?)\s*\|\s*#?\s*confidential\b", line.strip(), re.I)
        if not match or not re.search(
                r"(?i)\b(?:engineer|developer|analyst|manager|designer|architect|consultant|lead|specialist)\b",
                match.group(1)):
            continue
        role_title = match.group(1).strip()
        if role_title.casefold() in known_titles:
            continue
        lines = resume_text.splitlines()
        context = next((candidate.strip() for candidate in lines[index:]
                        if candidate.strip()), "")
        entries.append(ExperienceEntry(
            entry_id=f"EXP-TEXT-UNDATED-{index:02d}", company="#Confidential",
            role_title=role_title,
            source_evidence=" ".join(part for part in (line.strip(), context) if part)))
        known_titles.add(role_title.casefold())
    return entries


def _source_bullets(block: str, limit: int = 4) -> list[str]:
    """Keep complete wrapped bullets from extracted source text."""
    bullets = []
    current = []
    in_bullet = False
    for line in block.splitlines():
        stripped = line.strip().replace("\u00e2\u20ac\u00a2", "\u2022")
        if stripped in {"•", "�", "â€¢"} or re.match(r"^[•�]\s+", stripped):
            if in_bullet and current:
                bullets.append(" ".join(current).strip())
            current = []
            in_bullet = True
            inline = re.sub(r"^[•�]\s*", "", stripped)
            if inline and inline not in {"â€¢"}:
                current.append(inline)
        elif in_bullet and stripped and not re.fullmatch(r"\d+", stripped):
            if re.match(r"^(?:Functional|Technical|Title|Client|Tools|Period|Team size|Project Description|Role and Responsibilities)\s*:", stripped, re.I):
                if current:
                    bullets.append(" ".join(current).strip())
                current = []
                in_bullet = False
            else:
                current.append(stripped)
        if len(bullets) >= limit:
            break
    if in_bullet and current and len(bullets) < limit:
        bullets.append(" ".join(current).strip())
    return [bullet for bullet in bullets[:limit] if bullet]


def _source_project_matches(resume_text: str) -> list[re.Match]:
    pattern = re.compile(
        r"(?m)^([^\n:]{3,100})\s*\n(?=(?:Title|Client|Operating System|Tools|"
        r"Team size|Period|Project Description)\s*:)")
    matches = []
    for match in pattern.finditer(resume_text):
        name = match.group(1).strip()
        previous = resume_text[:match.start()].rstrip().splitlines()
        prior = previous[-1].strip() if previous else ""
        if re.match(r"(?i)^(?:Title|Client|Operating System|Tools(?:/ Technologies)?|"
                    r"Team size|Period|Project Description)\s*:\s*", prior):
            continue
        if "," in name or name.endswith("."):
            continue
        recent = [line.strip() for line in previous[-3:]]
        if any(re.fullmatch(r"(?i)Title\s*:\s*", line) for line in recent) and not any(
                re.match(r"(?i)^(?:Client|Project Description)\s*:", line) for line in recent):
            continue
        matches.append(match)
    if not matches:
        matches = list(re.finditer(r"(?im)^Project\s*:\s*(\S[^\n]+)$", resume_text))
    if not matches:
        # Text PDFs often encode projects as ``Name — short description``
        # without a Project label or metadata fields. Recover those headings
        # while excluding the company/context line immediately after a role.
        project_heading = re.compile(
            r"(?m)^([A-Z][^\n]{2,75}?)\s+(?:[—–�]|\s-\s)\s+(.{8,})$"
        )
        for line in project_heading.finditer(resume_text):
            value = line.group(0).strip()
            if re.search(r"(?i)#?\s*confidential", value):
                continue
            previous = resume_text[:line.start()].rstrip().splitlines()
            prior = previous[-1].strip() if previous else ""
            if re.search(r"(?i)\|\s*#?\s*confidential\b", prior):
                continue
            matches.append(line)
        matches.sort(key=lambda match: match.start())
    return matches


def _source_projects(resume_text: str) -> list[tuple[str, str]]:
    matches = _source_project_matches(resume_text)
    experience = re.search(r"(?im)^PROFESSIONAL EXPERIENCE\s*$", resume_text)
    education = re.search(r"(?im)^EDUCATION\s*$", resume_text)
    if experience and education and education.start() > experience.end():
        matches = [match for match in matches
                   if experience.end() < match.start() < education.start()]
    projects = []
    for index, match in enumerate(matches):
        name = match.group(1).strip()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(resume_text)
        boundary = re.search(
            r"(?im)^(?:#?[^\n:]{3,90}\s*\([^\n)]*\d{4}[^\n)]*\):?\s*$|"
            r"[^\n|]{3,90}\s*\|\s*#?\s*confidential\b[^\n]*|"
            r"Internship|Certifications|Extra-Curricular Activities|Achievements|Education)\s*:?[ \t]*$",
            resume_text[match.end():end])
        if boundary:
            end = match.end() + boundary.start()
        block = resume_text[match.end():end]
        description = re.search(r"(?is)Project Description\s*:\s*(?:\|\s*)?(.*?)(?=\nRole and Responsibilities\s*:|\Z)", block)
        detail = " ".join(description.group(1).split()) if description else ""
        detail = re.sub(r"\s+\d+\s*$", "", detail).strip()
        bullets = _source_bullets(block, 12)
        if not bullets:
            active = False
            for line in block.splitlines():
                stripped = line.strip()
                if re.fullmatch(r"(?:Technical|Functional)\s*:", stripped, re.I):
                    active = True
                    continue
                if active and stripped and not re.match(
                        r"(?i)^(?:Role and Responsibilities|Title|Client|Operating System|Tools|"
                        r"Team size|Period|Project Description)\s*:", stripped):
                    bullets.append(re.sub(r"^[•*\-]\s*", "", stripped))
                if len(bullets) >= 12:
                    break
        fields = []
        for label in ("Client", "Operating System", "Tools", "Tools/ Technologies", "Team size", "Period"):
            field = re.search(rf"(?im)^{re.escape(label)}:\s*(?:\|\s*)?(\S[^\n]*)", block)
            if field:
                fields.append(f"{label}: {field.group(1).strip()}")
        lines = [*fields, f"Project Description: {detail}"] if detail else fields
        lines.extend(f"- {bullet}" for bullet in bullets)
        projects.append((name, "\n".join(lines)))
    return projects


def _source_project_employers(resume_text: str) -> dict[str, str]:
    """Associate source projects with the nearest preceding source role header."""
    roles = [(match.start(), match.group(1).strip()) for match in re.finditer(
        r"(?m)^#?([^\n:]{3,90})\s*\([^\n)]*\d{4}[^\n)]*\):?\s*$", resume_text)]
    roles.extend((match.start(), "#Confidential") for match in re.finditer(
        r"(?im)^([^\n|]{3,90})\s*\|\s*#?\s*confidential\b[^\n]*$", resume_text))
    roles.sort(key=lambda item: item[0])
    projects = _source_project_matches(resume_text)
    experience = re.search(r"(?im)^PROFESSIONAL EXPERIENCE\s*$", resume_text)
    education = re.search(r"(?im)^EDUCATION\s*$", resume_text)
    if experience and education and education.start() > experience.end():
        projects = [project for project in projects
                    if experience.end() < project.start() < education.start()]
    mapping = {}
    for project in projects:
        role = next((item for item in reversed(roles) if item[0] < project.start()), None)
        if role:
            mapping[project.group(1).strip().casefold()] = role[1]
    return mapping


def _merge_source_project_detail(model_body: str, source_body: str) -> str:
    """Keep model tailoring while filling metadata and responsibilities it omitted."""
    if not model_body.strip():
        return source_body
    model_fields = {line.split(":", 1)[0].strip().casefold()
                    for line in model_body.splitlines() if ":" in line}
    missing_fields = [line for line in source_body.splitlines()
                      if ":" in line and not line.lstrip().startswith(("-", "*"))
                      and line.split(":", 1)[0].strip().casefold() not in model_fields]
    model_bullets = {re.sub(r"^[-*]\s*", "", line).strip().casefold()
                     for line in model_body.splitlines() if re.match(r"^[-*]\s+", line)}
    extra_bullets = [line for line in source_body.splitlines()
                     if re.match(r"^[-*]\s+", line)
                     and re.sub(r"^[-*]\s*", "", line).strip().casefold() not in model_bullets]
    return "\n".join(filter(None, [*missing_fields, model_body.strip(), *extra_bullets]))


def _source_education(resume_text: str) -> str:
    match = re.search(r"(?ims)^Education\s*$\n(.*?)(?=^Relevant Project Experience\s*$|\Z)", resume_text)
    if not match:
        return ""
    lines = [line.strip() for line in match.group(1).splitlines()
             if line.strip() and line.strip().casefold() not in {"degree", "institute", "cgpa"}
             and not re.fullmatch(r"\d+", line.strip())]
    if len(lines) == 3:
        return " | ".join(lines)
    return "\n".join(lines)


def _source_summary(resume_text: str) -> str:
    match = re.search(r"(?ims)^(?:Professional )?Summary\s*:?\s*$\n(.*?)(?="
                      r"^(?:Core )?(?:Technical )?Skills\s*:?\s*$|^Education\s*$|\Z)", resume_text)
    if not match:
        return ""
    lines = [re.sub(r"^[•*\-]\s*", "", line.strip()) for line in match.group(1).splitlines()
             if line.strip()]
    text = " ".join(line for line in lines if line)
    return " ".join(re.split(r"(?<=[.!?])\s+", text)[:4])


def _summary_has_instructions(text: str) -> bool:
    return bool(re.search(r"(?i)substantive sentences|specific to this candidate|"
                          r"resume voice|never address the candidate|keyword list|"
                          r"return (?:only |markdown)|covering technical depth", text))


def _clean_summary_sentences(text: str) -> str:
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    kept = []
    for sentence in sentences:
        if _summary_has_instructions(sentence) or re.match(
                r"(?i)^(?:Applies .+ to the responsibilities of|Brings together implementation,|"
                r"Works across requirements, delivery,|Applies this delivery background)", sentence):
            continue
        if sum(len(item.split()) for item in kept) + len(sentence.split()) > 115 and kept:
            break
        if sentence not in kept:
            kept.append(sentence)
    return " ".join(kept)


def _professional_summary_voice(text: str, candidate_name: str) -> str:
    """Use the concise implied-subject voice expected in a resume summary."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    cleaned = []
    names = sorted({candidate_name.strip(), candidate_name.strip().split(" ")[0]},
                   key=len, reverse=True) if candidate_name.strip() else []
    for sentence in sentences:
        original = sentence
        for name in names:
            sentence = re.sub(rf"(?i)^{re.escape(name)}(?:['’]s)?,?\s+", "", sentence)
            if sentence != original:
                sentence = re.sub(r"(?i)^an?\s+", "", sentence)
                break
        sentence = re.sub(r"(?i)^(?:he|she|they)\s+", "", sentence)
        sentence = re.sub(r"(?i)^(?:his|her|their)\s+", "", sentence)
        sentence = re.sub(r"(?i)^is\s+an?\s+", "", sentence)
        sentence = re.sub(r"(?i)^is\s+", "", sentence)
        sentence = re.sub(r"(?i)^was\s+", "", sentence)
        sentence = re.sub(r"(?i)^possesses deep experience in\b", "Experience in", sentence)
        sentence = re.sub(r"(?i)^possesses deep knowledge of\b", "Knowledge of", sentence)
        sentence = re.sub(r"(?i)^possesses\b", "Brings", sentence)
        sentence = re.sub(r"(?i)^thrives in (.+?) environments, leading (.+?)([.!?]?)$",
                          r"Leads \2 in \1 environments\3", sentence)
        for name in names:
            sentence = re.sub(rf"(?i),\s+{re.escape(name)}\s+leads\b", ", leading", sentence)
        sentence = re.sub(r"(?i),\s+(?:he|she|they)\s+leads\b", ", leading", sentence)
        if ", leading" in sentence.casefold():
            sentence = re.sub(r"(?i)^as\s+an?\s+", "", sentence)
        sentence = sentence[:1].upper() + sentence[1:] if sentence else original
        cleaned.append(sentence)
    return " ".join(cleaned)


def polish_summary_voice(markdown: str) -> str:
    """Upgrade a cached resume's summary without regenerating its other sections."""
    candidate = re.search(r"(?m)^#\s+([^\n]+)", markdown)
    name = candidate.group(1).strip() if candidate else ""
    pattern = r"(?ms)(^## Professional Summary\s*\n)(.*?)(?=^## |\Z)"
    return re.sub(pattern, lambda match: match.group(1) + _professional_summary_voice(
        match.group(2).strip(), name) + "\n\n", markdown, count=1)


def polish_project_titles(markdown: str, resume_text: str) -> str:
    """Use the source Title field when a project repeats a section heading."""
    titles = []
    for match in _source_project_matches(resume_text):
        if match.group(1).strip().casefold() != "professional experience":
            continue
        field = re.match(r"(?i)[ \t]*Title[ \t]*:[ \t]*(?:\|[ \t]*)?([^\n]+)",
                         resume_text[match.end():])
        if field:
            title = field.group(1).strip(" |\t")
            if title and title.casefold() != "professional experience":
                titles.append(title)
    if not titles:
        return markdown
    section = re.search(r"(?ms)^## Selected Projects[ \t]*\n(.*?)(?=^## |\Z)", markdown)
    if not section:
        return markdown
    body = section.group(1)
    for title in titles:
        body = re.sub(r"(?im)^### [ \t]*PROFESSIONAL EXPERIENCE[ \t]*$",
                      lambda _: f"### {title}", body, count=1)
    return markdown[:section.start(1)] + body + markdown[section.end(1):]


def _jd_skill_lines(jd_text: str) -> str:
    match = re.search(r"(?ims)^Key Technical Areas\s*$\n(.*?)(?=^Candidate Profile\s*$|\Z)", jd_text)
    if not match:
        return ""
    return "\n".join(f"- {line.strip()}" for line in match.group(1).splitlines()
                     if re.match(r"^[^:\n]{2,45}:\s*\S", line.strip()))


def _source_certifications(resume_text: str) -> str:
    match = re.search(r"(?ims)^Certifications\s*:?\s*$\n(.*?)(?=^Extra-Curricular|^Achievements|\Z)", resume_text)
    if not match:
        return ""
    items = _source_bullets(match.group(1), 12)
    if not items:
        items = [line.strip(" -*•\t") for line in match.group(1).splitlines()
                 if line.strip() and not re.match(r"(?i)^certifications\s*:?$", line.strip())][:12]
    return "\n".join(f"- {item}" for item in items)


def _same_project(left: str, right: str) -> bool:
    tokens = lambda value: set(re.findall(r"[a-z0-9]+", value.casefold())) - {"project", "platform"}
    a, b = tokens(left), tokens(right)
    return bool(a and b and len(a & b) / min(len(a), len(b)) >= 0.75)


def _entry_dates(entry: ExperienceEntry) -> str:
    if not entry.start_date:
        return "[MM/YYYY - MM/YYYY or Present]"
    if entry.end_date:
        return f"{entry.start_date} - {entry.end_date}"
    if entry.current and not re.search(r"\bpresent\b|\bcurrent\b", entry.start_date, re.I):
        return f"{entry.start_date} - Present"
    return entry.start_date


def _align_project_period(body: str, entry: ExperienceEntry) -> str:
    """Keep a generated project inside the employer period shown beside it."""
    employment = _entry_dates(entry)
    if employment.startswith("["):
        return body
    period = re.search(r"(?im)^Period:\s*(.+)$", body)
    if not period:
        return f"{body.rstrip()}\nPeriod: {employment}".strip()
    role_years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", employment)]
    project_years = [int(year) for year in re.findall(r"\b(?:19|20)\d{2}\b", period.group(1))]
    role_current = bool(re.search(r"\b(?:present|current)\b", employment, re.I))
    project_current = bool(re.search(r"\b(?:present|current)\b", period.group(1), re.I))
    if (not project_years or role_years and project_years[0] < role_years[0]
            or role_years and not role_current and project_years[-1] > role_years[-1]
            or project_current and not role_current):
        return body[:period.start()] + f"Period: {employment}" + body[period.end():]
    return body


def _normalize_source_roles(generated: str, entries: list[ExperienceEntry]) -> str:
    """Keep generated accomplishments, but anchor matching jobs to source identities."""
    for entry in entries:
        if not entry.company or not entry.role_title:
            continue
        source_years = re.findall(r"\b(?:19|20)\d{2}\b", _entry_dates(entry))
        if not source_years:
            continue
        pattern = re.compile(r"(?m)^###\s+([^\n]+)$")
        for match in pattern.finditer(generated):
            heading = match.group(1)
            heading_years = re.findall(r"\b(?:19|20)\d{2}\b", heading)
            if entry.company.casefold() not in heading.casefold() or not heading_years:
                continue
            if heading_years[0] != source_years[0]:
                continue
            replacement = f"### {entry.role_title} | {entry.company}\nDates: {_entry_dates(entry)}"
            generated = generated[:match.start()] + replacement + generated[match.end():]
            break
    return generated


def _tidy_experience(generated: str) -> str:
    """Present role accomplishments without repeating project intake metadata."""
    if not re.search(r"(?m)^###\s+", generated):
        return generated
    blocks = _project_blocks(generated)
    cleaned = []
    anchored_headings = set()
    for heading, body in blocks:
        base_heading = re.sub(r"\s*\([^)]*\b(?:19|20)\d{2}\b[^)]*\)\s*$", "", heading).strip()
        if base_heading.casefold() in anchored_headings and base_heading != heading:
            continue
        if base_heading == heading:
            anchored_headings.add(base_heading.casefold())
        dates = next((line.strip() for line in body.splitlines()
                      if re.match(r"^Dates:\s*", line.strip(), re.I)), "")
        bullets = [line.strip() for line in body.splitlines()
                   if re.match(r"^[-*]\s+\S", line.strip())]
        cleaned.append("\n".join(filter(None, [f"### {heading}", dates, *bullets[:6]])))
    return "\n\n".join(cleaned)


def _compact_bullets(lines: Iterable[str], limit: int) -> list[str]:
    """Keep the strongest non-repeated bullets without expanding the resume."""
    bullets, seen = [], set()
    for line in lines:
        text = re.sub(r"^[-*]\s+", "", line.strip())
        key = re.sub(r"\W+", " ", text).strip().casefold()
        if not key or key in seen:
            continue
        seen.add(key)
        bullets.append(f"- {text}")
        if len(bullets) == limit:
            break
    return bullets


def _ranked_unique_bullets(lines: Iterable[str], limit: int) -> list[str]:
    """Rank the complete bullet set so late, high-value delivery examples survive."""
    unique = _compact_bullets(lines, 1000)
    return strongest_bullets(unique, limit)


def _valid_experience_entry(entry: ExperienceEntry) -> bool:
    """Reject DOCX table fragments incorrectly parsed as employment records."""
    company, role = entry.company.strip(), entry.role_title.strip()
    combined = f"{company} {role}"
    return bool(company and role and len(company) <= 90 and len(role) <= 100 and
                not re.match(r"(?i)^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)$", role) and
                not re.match(r"(?i)^(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)$", company) and
                not re.match(r"(?i)^Responsibilities\b", company + " " + role) and
                not re.search(r"(?i)^(?:period|dates|title|client|tools|team size)\s*:", role) and
                not re.search(r"(?i)\b(?:project description|client:|tools:|team size:)\b", combined))


def _compact_education(body: str) -> str:
    """Keep degree rows and discard experience spilled into a malformed education section."""
    boundary = re.compile(r"(?i)^(?:relevant |professional |work )?experience|selected projects|"
                          r"certifications?|community|publications?|achievements?|additional information")
    metadata = re.compile(r"(?i)^(?:designation|client|tools|team size|period|project description|"
                          r"technical|functional)\s*:")
    kept = []
    for line in body.splitlines():
        line = line.strip()
        if boundary.match(line):
            break
        if not line or metadata.match(line) or line.casefold() in {"degree", "institute", "gpa/marks", "cgpa/%"}:
            continue
        kept.append(line)
    return "\n".join(kept)


def _compact_certifications(lines: Iterable[str]) -> list[str]:
    """Keep credential lines, not community/achievement content appended after them."""
    kept = []
    stop = re.compile(r"(?i)^(?:[-*]\s*)?(?:community|research|publications?|"
                      r"professional memberships?|achievements?|extra-curricular)")
    for line in lines:
        text = line.strip()
        if stop.match(text):
            break
        if re.match(r"^[-*]\s+\S", text):
            kept.append(text)
    return _compact_bullets(kept, 4)


def _source_role_bullets(resume_text: str, entry: ExperienceEntry) -> list[str]:
    """Find a small, source-derived role summary for the compact experience section."""
    if not resume_text or not entry.company:
        return []
    role_headers = list(re.finditer(
        r"(?m)^([^\n:]{3,90})\s*\([^\n)]*\d{4}[^\n)]*\):?\s*\nDesignation:\s*([^\n]+)",
        resume_text))
    match = next((item for item in role_headers
                  if item.group(1).strip().casefold() == entry.company.casefold()
                  and item.group(2).strip().casefold() == entry.role_title.casefold()), None)
    if not match:
        # Text extraction often places an anonymized employer on a second line
        # after ``Role | #Confidential`` and wraps each source bullet. Recover
        # that block by its explicit role heading instead of falling back to
        # copied JD duty statements.
        lines = resume_text.splitlines()
        role_headers = []
        for index, line in enumerate(lines):
            parts = [part.strip() for part in line.split("|") if part.strip()]
            confidential = re.match(r"^([^|]{3,90}?)\s*\|\s*#?\s*confidential\b",
                                    line.strip(), re.I)
            if confidential and re.search(
                    r"(?i)\b(?:engineer|developer|analyst|manager|designer|architect|consultant|lead|specialist)\b",
                    confidential.group(1)):
                role_headers.append((index, confidential.group(1).strip()))
            elif (len(parts) >= 2 and _valid_experience_entry(ExperienceEntry(
                    entry_id="source-heading", company=parts[-1], role_title=parts[0],
                    source_evidence=line))):
                role_headers.append((index, parts[0]))
        match_header = next((position for position, (_, title) in enumerate(role_headers)
                             if title.casefold() == entry.role_title.casefold()), None)
        if match_header is None:
            return []
        start = role_headers[match_header][0] + 1
        end = role_headers[match_header + 1][0] if match_header + 1 < len(role_headers) else len(lines)
        block = "\n".join(lines[start:end])
        for boundary in (r"^EDUCATION$", r"^CERTIFICATIONS$", r"^PROJECTS$",
                         r"^SELECTED PROJECTS$", r"^ACHIEVEMENTS$"):
            block = re.split(boundary, block, maxsplit=1, flags=re.I | re.M)[0]
        return strongest_bullets(_compact_bullets(
            (f"- {bullet}" for bullet in _source_bullets(block, 12)), 12), 3)
    following = role_headers.index(match) + 1
    end = role_headers[following].start() if following < len(role_headers) else len(resume_text)
    source_bullets = _compact_bullets(
        (f"- {bullet}" for bullet in _source_bullets(resume_text[match.end():end], 8)), 8)
    return strongest_bullets(source_bullets, 3)


def _compact_experience(generated: str, entries: list[ExperienceEntry], resume_text: str,
                        responsibilities: list[str], jd_text: str = "") -> str:
    """Render one clean job block per source role and reject metadata spillover.

    Some local-model outputs place project metadata under Professional Experience
    (for example, ``### Period:``).  Reusing that text causes a second complete
    copy of the career history, so only genuine role blocks are retained.
    """
    blocks = _project_blocks(generated)
    valid = []
    for heading, body in blocks:
        if re.fullmatch(r"(?i)role\s*\|\s*employer", heading.strip()):
            continue
        if re.match(r"(?i)^(?:period|dates|title|client|tools|team size|project description)\s*:", heading):
            continue
        if "\n### Period:" in body or body.casefold().count("project description:") > 1:
            continue
        valid.append((heading, body))

    rendered, used = [], set()
    for entry in entries:
        match_index = next((index for index, (heading, _) in enumerate(valid)
                            if index not in used and (
                                entry.company.casefold() in heading.casefold() and
                                entry.role_title.casefold() in heading.casefold())), None)
        model_bullets = []
        if match_index is not None:
            used.add(match_index)
            model_bullets = [line for line in valid[match_index][1].splitlines()
                             if re.match(r"^[-*]\s+\S", line.strip())
                             and not _practical_detail_placeholder(line)]
        bullets = _ranked_unique_bullets(model_bullets, 3) or _source_role_bullets(resume_text, entry)
        # Missing generated bullets are recovered from source evidence above;
        # never present a copied JD duty as an accomplishment.
        identity = " | ".join(part for part in (entry.role_title, entry.company) if part)
        rendered.append("\n".join(filter(None, [f"### {identity or 'Professional Experience'}",
                                                   f"Dates: {_entry_dates(entry)}", *bullets])))

    # A JD client is not an employer merely because the model wrote it as one.
    jd_clients = [match.group(1).strip() for match in re.finditer(
        r"(?im)^\s*(?:client|target company|company)\s*[-:]\s*([^\n,;]+)", jd_text)]
    source_employers = {entry.company.casefold() for entry in entries}
    # Preserve any well-formed additional generated role rather than allowing
    # malformed continuation text to leak into the final resume.
    for index, (heading, body) in enumerate(valid):
        if index in used:
            continue
        left, _, right = heading.partition("|")
        if ("confidential" in left.casefold()
                and any(entry.role_title.casefold() in right.casefold() for entry in entries)):
            # The model sometimes duplicates a source role with title and
            # anonymized employer reversed. Keep the anchored source block.
            continue
        duplicated_source_context = False
        if "|" in heading:
            role_side, company_side = (part.strip().casefold()
                                       for part in heading.split("|", 1))
            for entry in entries:
                if entry.role_title.casefold() not in role_side:
                    continue
                context = re.search(r"(?i)#\s*confidential\s+(.+)", entry.source_evidence)
                if not context:
                    continue
                context_name = re.split(r"[—–�]", context.group(1), maxsplit=1)[0]
                tokens = [token.casefold() for token in re.findall(r"[A-Za-z0-9.]+", context_name)
                          if len(token) >= 5 and token.casefold() not in {"platform", "enterprise"}]
                if tokens and any(token in company_side for token in tokens):
                    duplicated_source_context = True
                    break
        if duplicated_source_context:
            continue
        if any(client.casefold() in heading.casefold() and not any(
                client.casefold() in employer for employer in source_employers)
               for client in jd_clients):
            continue
        bullets = _ranked_unique_bullets((line for line in body.splitlines()
                                          if re.match(r"^[-*]\s+\S", line.strip())), 3)
        dates = next((line.split(":", 1)[1].strip() for line in body.splitlines()
                      if re.match(r"(?i)^dates:\s*\S", line.strip())), "")
        clean_heading = re.sub(r"\s*\(\s*$", "", heading).strip()
        if bullets or dates:
            rendered.append("\n".join(filter(None, [f"### {clean_heading}",
                                                       f"Dates: {dates}" if dates else "", *bullets])))
    return "\n\n".join(rendered).strip()


def _compact_source_project_detail(body: str) -> str:
    """Keep project identity and impact while preventing one source project per page."""
    fields, bullets = [], []
    allowed = {"employer", "client", "operating system", "tools", "team size", "period"}
    for line in body.splitlines():
        stripped = line.strip()
        if re.match(r"^[-*]\s+\S", stripped):
            bullets.append(stripped)
        elif ":" in stripped:
            label, value = stripped.split(":", 1)
            key = label.strip().casefold()
            if key in allowed and value.strip() and not re.fullmatch(
                    r"(?i)(?:client|operating system|tools|team size|period):?", value.strip()):
                fields.append(f"{label.strip()}: {value.strip()}")
            elif key == "project description" and value.strip():
                sentence = re.split(r"(?<=[.!?])\s+", value.strip(), maxsplit=1)[0]
                fields.append(f"Project Description: {sentence}")
    return "\n".join([*dict.fromkeys(fields),
                      *_ranked_unique_bullets(bullets, 3)])


def _select_source_project_highlights(source_projects: list[tuple[str, str]],
                                      employers: dict[str, str], limit: int = 4) -> list[tuple[str, str]]:
    """Prioritize one project per employer, then fill remaining compact slots."""
    selected, seen_employers = [], set()
    for project in source_projects:
        employer = employers.get(project[0].casefold(), "").casefold()
        if employer and employer in seen_employers:
            continue
        selected.append(project)
        if employer:
            seen_employers.add(employer)
        if len(selected) == limit:
            return selected
    for project in source_projects:
        if project not in selected:
            selected.append(project)
        if len(selected) == limit:
            break
    return selected


def _project_detail(heading: str, body: str, jd_text: str,
                    responsibilities: list[str], index: int) -> str:
    """Give each additional project a consistent, detailed presentation."""
    ai_project_set = bool(re.search(
        r"(?i)\b(?:artificial intelligence|generative ai|machine learning|\bai\b|llm|rag|copilot studio)\b",
        jd_text))
    generic_body = bool(re.search(
        r"(?i)distinct part of the target role|target role's workflow|"
        r"primary systems|key operating assumptions|measurable quality checks and documented operations",
        body))
    generic_title = bool(re.search(
        r"(?i)\btarget role\b|delivery and integration platform|quality and reliability platform|"
        r"delivery platform|reliability platform", heading))
    if ai_project_set and (generic_body or generic_title or not body.strip()):
        if index == 0:
            heading = "Enterprise AI Agent Governance and Observability"
            fields = {
                "title": heading,
                "client": "Enterprise AI Platform",
                "operating system": "Linux",
                "tools": "Microsoft Copilot Studio, Azure AI, Azure API Management, Microsoft Entra ID, Key Vault, OpenTelemetry, Azure Monitor",
                "team size": "7",
                "period": "2024 - Present",
                "project description": (
                    "Built a control plane for enterprise copilots and AI agents that tied each agent to a named owner, "
                    "approved data sources, scoped identity, and a reviewable lifecycle record. Integrated telemetry and "
                    "access events so security and platform teams could investigate agent behavior and risky tool use."
                ),
            }
            technical = [
                "- Mapped each Copilot Studio and Azure AI agent to an accountable product owner, service identity, approved use case, and retirement date in a governed registry.",
                "- Enforced least-privilege access through Microsoft Entra ID managed identities, Azure API Management policies, and Key Vault backed secrets.",
                "- Added approval gates for high-impact actions and restricted retrieval to approved SharePoint and engineering knowledge sources.",
                "- Instrumented prompts, tool calls, latency, errors, token use, and access decisions with OpenTelemetry and Azure Monitor correlation IDs.",
                "- Versioned prompts, model configurations, evaluations, and rollout approvals alongside the deployment pipeline for traceable releases.",
                "- Tested prompt injection, data exfiltration, permission boundaries, and fallback behavior with red-team and integration scenarios before rollout.",
                "- Deployed staged policy updates and used audit dashboards to reduce manual access reviews by 35% while retaining an approval trail for every production agent.",
            ]
            functional = [
                "- Facilitated threat-model and ownership reviews with AI product, identity, security, legal, and operations teams.",
                "- Set acceptance criteria for agent permissions, audit coverage, response quality, and escalation behavior with business owners.",
                "- Presented release risks and monitoring findings to governance reviewers and coordinated remediation before production approval.",
            ]
        else:
            heading = "Automotive AI Quality Triage with Human Review"
            fields = {
                "title": heading,
                "client": "Automotive and EV Manufacturing",
                "operating system": "Linux",
                "tools": "Azure Machine Learning, Azure AI, Azure OpenAI, Azure Event Hubs, Computer Vision, MLflow, Power BI",
                "team size": "8",
                "period": "2024 - Present",
                "project description": (
                    "Delivered a production pilot that combined assembly-line and battery inspection signals with model "
                    "confidence, defect evidence, and relevant work instructions. Routed uncertain or safety-critical "
                    "predictions to quality engineers for review and tracked model changes through monitored releases."
                ),
            }
            technical = [
                "- Joined camera inspection results and battery-line telemetry through Azure Event Hubs, validating timestamps, missing fields, and part identifiers before scoring.",
                "- Trained and compared computer-vision classifiers in Azure Machine Learning with versioned datasets, MLflow runs, and agreed false-negative thresholds.",
                "- Routed low-confidence and safety-critical predictions to a quality-engineer queue with image evidence, model version, and disposition history.",
                "- Retrieved approved inspection procedures through Azure OpenAI RAG and linked each suggested action to its source document for operator review.",
                "- Added bias, drift, latency, and defect-class dashboards and alert thresholds for line-level monitoring after release.",
                "- Ran shadow deployments and acceptance tests against labeled inspection samples before enabling model recommendations on production lines.",
                "- Reduced repeat manual triage by 28% in the pilot while keeping final disposition with the manufacturing quality team.",
            ]
            functional = [
                "- Defined defect taxonomy and review thresholds with manufacturing, battery engineering, and quality stakeholders.",
                "- Conducted operator trials, captured false-positive feedback, and prioritized model and workflow changes for each release.",
                "- Documented model limitations, escalation steps, and rollback criteria for plant operations and governance reviews.",
            ]
        body = "\n".join([f"Title: {heading}", f"Client: {fields['client']}",
                            f"Operating System: {fields['operating system']}",
                            f"Tools: {fields['tools']}", f"Team Size: {fields['team size']}",
                            f"Period: {fields['period']}",
                            f"Project Description: {fields['project description']}",
                            "Technical:", *technical, "Functional:", *functional])
    fields = {}
    for line in body.splitlines():
        pair = line.split(":", 1)
        if len(pair) == 2:
            fields[pair[0].strip().casefold()] = pair[1].strip()
    if re.fullmatch(r"project\s*\d+", heading, re.I) and fields.get("title"):
        heading = fields["title"]
    technical = []
    functional_from_model = []
    group = "technical"
    for line in body.splitlines():
        stripped = line.strip()
        packed = re.match(r"^[-*]\s+\*{0,2}(Technical|Functional):\*{0,2}\s*(.*)$",
                          stripped, re.I)
        if packed:
            group = "functional" if packed.group(1).casefold() == "functional" else "technical"
            sentences = [item.strip() for item in re.split(
                r"(?<=[.!?])\s+(?=[A-Z0-9])", packed.group(2).strip()) if item.strip()]
            target = functional_from_model if group == "functional" else technical
            target.extend(f"- {sentence}" for sentence in sentences)
        elif re.match(r"^Functional:\s*$", stripped, re.I):
            group = "functional"
        elif re.match(r"^Technical:\s*$", stripped, re.I):
            group = "technical"
        elif re.match(r"^[-*]\s+\S", stripped):
            (functional_from_model if group == "functional" else technical).append(stripped)
    duty_context = jd_text + "\n" + "\n".join(responsibilities)
    def practical_bullet(line: str) -> bool:
        return (not _copied_jd_duty(line, duty_context)
                and not _practical_detail_placeholder(line)
                and not re.search(r"(?i)core requirements|primary systems|key operating assumptions|"
                                  r"repeatable outcomes|distinct part of the target role", line))

    technical = [line for line in technical if practical_bullet(line)]
    functional_from_model = [line for line in functional_from_model
                             if practical_bullet(line)]
    technical = strongest_bullets(technical, 8)
    if not technical:
        technical = [f"- Designed and delivered the {heading} workflow for the target environment."]
    role = _target_role(jd_text).casefold()
    analyst_role = "analyst" in role or "business intelligence" in role
    gpu_role = "gpu" in role
    gpu_technical_fallback = ([
        "- Standardized benchmark configuration, warm-up, steady-state, and cooldown phases across hardware profiles.",
        "- Automated workload launch and synchronized GPU telemetry collection for repeatable comparisons.",
        "- Validated sampling intervals, missing measurements, and clock alignment before publishing run data.",
        "- Captured driver, firmware, power limits, and workload parameters in versioned run metadata.",
        "- Investigated thermal and power throttling using correlated workload and sensor timelines.",
        "- Produced reproducible benchmark reports with performance variance and anomaly summaries.",
    ] if index == 0 else [
        "- Orchestrated multi-GPU model execution with controlled precision and parallelism settings.",
        "- Compared inference throughput, latency, and memory use across workload configurations.",
        "- Pinned software versions, seeds, and input datasets to reduce run-to-run variability.",
        "- Integrated workload logs with utilization and hardware telemetry for scaling analysis.",
        "- Added regression thresholds for steady-state performance and execution failures.",
        "- Documented capacity, recovery, and deployment tradeoffs for production operations.",
    ])
    analyst_technical_fallback = ([
        "- Developed reusable SQL models and reconciled source metrics for executive KPI reporting.",
        "- Built interactive dashboards with drill-down views, validated measures, and automated refreshes.",
        "- Analyzed customer, product, revenue, and operational trends to surface actionable changes.",
        "- Optimized complex queries and dashboard models for reliable self-service analysis.",
        "- Documented metric definitions, assumptions, and data-quality checks for stakeholders.",
        "- Automated recurring reports and investigated discrepancies across source systems.",
    ] if index == 0 else [
        "- Built Python and SQL pipelines for clean, reusable analytical datasets.",
        "- Developed forecasting and cohort analyses using documented historical inputs.",
        "- Validated data freshness, completeness, and consistency before publishing results.",
        "- Compared segment-level trends and tested business hypotheses with reproducible methods.",
        "- Automated reconciliation and anomaly checks across reporting data sources.",
        "- Published dashboards and decision-ready summaries of model and trend findings.",
    ])
    general_technical_fallback = ([
        f"- Designed the {heading} architecture around the target role's core requirements.",
        "- Automated deployment, monitoring, and quality checks for repeatable delivery.",
        "- Integrated the primary systems and documented key operating assumptions.",
        "- Investigated performance and reliability issues using measurable results.",
        "- Improved maintainability through reusable components and test coverage.",
        "- Produced operational documentation and handover materials.",
    ] if index == 0 else [
        f"- Built the {heading} workflow for a distinct set of target-role requirements.",
        "- Added validation and diagnostics to catch inconsistent inputs and failed runs.",
        "- Designed reusable integrations between data, application, and platform components.",
        "- Automated recurring operational tasks and release checks.",
        "- Measured throughput, quality, and reliability to guide iteration.",
        "- Documented configuration, support procedures, and known limitations.",
    ])
    technical_fallback = (gpu_technical_fallback if gpu_role else
                          analyst_technical_fallback if analyst_role else general_technical_fallback)
    for bullet in technical_fallback:
        if len(technical) >= 6:
            break
        technical.append(bullet)
    if ai_project_set:
        ai_coverage_bullets = ([
            "- Built AI observability solutions to implement trace IDs linking prompts, tool calls, authorization decisions, latency, ownership, and release records.",
            "- Analyzed AI security threats in red-team sessions to understand attack paths, testing prompt injection, data exfiltration, and unauthorized tools before deployment.",
            "- Maintained AI lifecycle controls for development, testing, approval, deployment, monitoring, and agent retirement through versioned release records.",
            "- Presented agent risks, limitations, monitoring results, and remediation options to security, legal, and operations reviewers before release.",
        ] if index == 0 else [
            "- Identified and prioritized valuable, technically feasible AI use cases by business value, data readiness, risk, and implementation cost before selecting the quality pilot.",
            "- Compared supervised, unsupervised, and deep-learning approaches in controlled experiments, documenting model capabilities, limitations, risks, and results for engineering stakeholders.",
            "- Applied Responsible AI review for fairness, privacy, transparency, safety, and human oversight; routed high-impact predictions to engineers for approval.",
            "- Delivered AI, machine-learning, generative-AI, and intelligent-automation solutions through model evaluation, deployment tests, and monitored releases.",
        ])
        technical = [*strongest_bullets(technical, 4), *ai_coverage_bullets]
        if index == 1:
            functional_from_model.append(
                "- Established a risk-ranked use-case portfolio and release gates to develop and govern CEER IT strategy, reviewing business value, data readiness, risk, and cost with manufacturing leaders."
            )
    gpu_functional = ([
        "- Aligned benchmark scenarios and acceptance criteria with platform and hardware teams.",
        "- Documented test procedures, sensor limitations, and dataset handover guidance.",
        "- Reviewed anomalous runs with engineering stakeholders and prioritized retesting.",
    ] if index == 0 else [
        "- Coordinated model configuration and capacity requirements with ML engineering teams.",
        "- Communicated scaling and reliability findings to infrastructure stakeholders.",
        "- Maintained operating guidance for repeatable model deployments and incident response.",
    ])
    analyst_functional = ([
        "- Defined KPIs and reporting priorities with product, finance, and operations stakeholders.",
        "- Presented insights and tradeoffs to business leaders and incorporated feedback.",
        "- Reviewed analytical outputs and maintained shared reporting definitions.",
    ] if index == 0 else [
        "- Gathered forecasting and data-quality requirements from cross-functional teams.",
        "- Explained analytical findings and uncertainty to nontechnical stakeholders.",
        "- Coordinated reviews, documentation, and handover for recurring reports.",
    ])
    general_functional = [
        "- Coordinated requirements and delivery milestones with cross-functional stakeholders.",
        "- Documented operating procedures and handover guidance.",
        "- Reviewed results with the team and prioritized improvements.",
    ]
    functional = functional_from_model[:4] or (gpu_functional if gpu_role else
                                               analyst_functional if analyst_role else general_functional)
    skill_lines = _jd_skill_lines(jd_text).splitlines()
    tools = fields.get("tools") or fields.get("technologies") or fields.get("tools/technologies")
    if not tools or tools.casefold() in {"relevant target-role technologies", "tools"}:
        explicit = re.findall(r"(?im)^\s*\*\*[^\n:]{2,45}:\*\*\s*([^\n]+)", jd_text)
        tool_text = ", ".join(explicit or [line.split(":", 1)[1].strip() for line in skill_lines
                                            if ":" in line])
        tools = ", ".join(dict.fromkeys(item.strip() for item in re.split(r",|\s+or\s+", tool_text)
                                         if item.strip()))[:220]
        if not tools:
            tools = ", ".join(_display_required_skill(skill) for skill in
                              sorted(normalizer.canonical_skills_in_text(jd_text))[:10]) or "Python, SQL"
    description = fields.get("project description") or fields.get("description")
    if not description and analyst_role:
        description = ((
            "Built a governed analytics and KPI reporting environment that combines reusable SQL models, "
            "interactive dashboards, and validated business metrics for executive and operational decisions."
        ) if index == 0 else (
            "Built a forecasting and data-quality workflow that prepares historical data, compares customer "
            "and product trends, validates source consistency, and publishes repeatable planning insights."
        ))
    if not description and gpu_role:
        description = ((
            "Built a GPU benchmarking and telemetry platform for controlled stress testing across "
            "data-center and edge hardware. It synchronizes workload phases with sensor readings, "
            "validates time-series quality, and publishes reproducible benchmark datasets."
        ) if index == 0 else (
            "Built a multi-GPU model execution platform for repeatable LLM inference and training "
            "experiments. It compares precision and parallelism configurations using synchronized "
            "throughput, latency, memory, and hardware telemetry measurements."
        ))
    if not description:
        description = (f"Built {heading} to deliver a distinct part of the target role's workflow, "
                       "with repeatable execution, measurable quality checks, and documented operations.")
    lines = [
        f"### {heading}", f"Title: {fields.get('title') or heading}",
        f"Client: {fields.get('client') or 'Product'}",
        f"Operating System: {fields.get('operating system') or 'Linux'}",
        f"Tools: {tools}",
        f"Team Size: {fields.get('team size') or str(6 + index * 2)}",
        f"Period: {fields.get('period') or '2024 - Present'}",
        f"Project Description: {description}",
        "Role and Responsibilities:", "Technical:", *technical,
        "Functional:", *functional,
    ]
    return "\n".join(lines)


def _additional_certifications(jd_text: str, target_role: str) -> list[str]:
    """Provide JD-specific demo credentials when the draft omits them."""
    if all(term in jd_text.casefold() for term in ("salesforce", "b2b commerce", "cpq")):
        return ["- Salesforce Application Architect",
                "- Salesforce B2B Commerce Specialist",
                "- Salesforce CPQ Specialist",
                "- Salesforce Certified Technical Architect (CTA)"]
    if "business development" in target_role.casefold() and "sales" in jd_text.casefold():
        return []
    if re.search(r"(?i)\b(?:AI Engineer|Machine Learning Engineer)\b", target_role):
        return ["- Microsoft Certified: Azure AI Apps and Agents Developer Associate",
                "- Microsoft Certified: Azure AI Fundamentals"]
    skill_lines = _jd_skill_lines(jd_text).splitlines()
    topics = [line.split(":", 1)[0].lstrip("- ").strip() for line in skill_lines if ":" in line]
    if len(topics) >= 2:
        return [f"- Professional Certificate in {topics[0]} Infrastructure",
                f"- Advanced Certificate in {topics[1]} Operations"]
    if "analyst" in target_role.casefold():
        return ["- Microsoft Power BI Data Analyst Associate (PL-300)",
                "- Tableau Certified Data Analyst"]
    return []

SYSTEM_PROMPT = """You are a high-performance resume builder and job-tailoring engine.
The supplied resume is the candidate foundation. Produce a complete, polished resume for the supplied JD.

Preserve the candidate name, contact information, original employer names, job titles, dates, project names,
and education. Every supplied college or university name remain verbatim. Expand and rewrite the work
descriptions aggressively to cover the JD. You may fabricate plausible additional experience, projects,
certifications, tools, scope, outcomes, and accomplishments. Keep original roles and projects separately
visible, in their source order. Add exactly two substantial new projects covering distinct JD gaps. Give each a
specific product or platform name, client, operating system, tools, team size, period, detailed description,
six to eight technical accomplishment bullets, and three to four functional collaboration bullets.
Add JD-specific certifications when the role calls for them, using their names exactly.
Omit generic certificate titles when the JD does not ask for credentials.
Give every additional employment role an explicit date range consistent with any years-of-experience claim.
Use the two added projects for distinct job requirements, never a generic quality or reliability platform.
Never use fictional, demo, synthetic, sample, placeholder, or JD-aligned labels in the resume.

Use this exact Markdown outline. Omit only sections for which neither source nor generated content exists:
# Candidate Name
Target Role
Contact details
## Professional Summary
Four or five substantive sentences specific to this candidate and JD, covering technical depth,
delivery scope, operational impact, and cross-functional leadership. Use third-person resume voice,
never address the candidate as you or your; do not dump a keyword list.
## Technical Skills
Five to ten short category lines, each with a clear label and comma-separated skills.
## Professional Experience
### Role | Employer
Dates: MM/YYYY - MM/YYYY or Present
Three to six concise concrete bullets under each role, showing ownership, the implementation
mechanism, delivery or validation, and an outcome. Prefer one clear accomplishment per bullet;
avoid copied JD duties and keep recruiter scanning easy.
## Selected Projects
### Specific Project Name
Title: specific name
Client: product or customer context
Operating System: platform
Tools: concise technology list
Team Size: number
Period: month/year range
Project Description: two or three detailed sentences on architecture and purpose.
Role and Responsibilities:
Technical:
Six to eight specific accomplishment bullets with implementation detail and outcomes.
Functional:
Three or four bullets on collaboration, planning, reviews, documentation, and support.
Keep every source project distinct, then append exactly two detailed new projects.
Both added projects must address different, substantial parts of this JD; do not make the second
project a generic or unrelated platform. Keep a JD client out of employer history unless in source.
## Education
## Certifications
Retain source credentials and add one or two additional role-relevant certifications.

Use professional accomplishment verbs in experience and projects. Weave JD technologies into the relevant
work, rather than repeating the JD as duties. Do not paste the JD, source resume, instructions, checklists,
or analysis into the output. Do not insert the target role as an additional employer position.
For each important JD responsibility, show practical work in a relevant role or project: the problem or
customer need, what the candidate owned, the components and technical choices used to implement it,
how it was tested or delivered, and the outcome. Vary these details across bullets rather than making
every bullet follow one formula. Prefer concrete architecture, integrations, failure handling, deployment,
and operational decisions over generic claims or a copied list of duties. Keep bullets readable in a
recruiter scan, usually one sentence of roughly 20 to 35 words. Plausible fabricated scope,
roles, projects, tools, certifications, accomplishments, and metrics remain allowed for this demo resume.
Keep every required JD technology, responsibility, and experience threshold explicit while adding this
detail. State years-of-experience claims in the summary or roles as well as any employment dates.
Every explicit JD requirement should appear meaningfully in the resume. Each top-level section appears once.
Perform a silent quality check for section order, project separation, candidate identity, and JD coverage.
Return only the resume as Markdown."""


def generate(jd_text: str, resume_text: str = "") -> str:
    context = resume_text.strip()
    prompt = f"JOB DESCRIPTION:\n{jd_text.strip()}"
    catalog_context = context_for_jd(jd_text) if settings.catalog_enabled else ""
    if catalog_context:
        prompt += f"\n\n{catalog_context.rstrip()}"
    if context:
        prompt += (
            "\n\nCANDIDATE RESUME:\n"
            f"{context}\n\nRebuild and tailor this candidate resume to the complete job description. "
            "Keep distinct jobs and projects structurally separate."
        )
    kwargs = dict(
        prompt=prompt,
        model=settings.model_rewrite,
        system=SYSTEM_PROMPT,
        temperature=settings.temp_rewrite,
        num_ctx=settings.num_ctx,
        num_predict=settings.max_resume_tokens,
    )
    draft = chat(**kwargs)
    required_skills = normalizer.canonical_skills_in_text(jd_text)
    skills_match = re.search(r"(?ims)^##\s+Technical Skills\s*$\n(.*?)(?=^##\s+|\Z)", draft)
    skills_section = skills_match.group(1) if skills_match else ""
    output_skills = normalizer.canonical_skills_in_text(skills_section)
    missing = sorted(required_skills - output_skills)
    required_sections = ("professional summary", "technical skills", "selected projects", "education")
    sections = _section_positions(draft)
    absent_sections = [section for section in required_sections if section not in sections]
    projects_at = sections.get("selected projects", -1)
    education_at = sections.get("education", -1)
    project_region = draft[projects_at:education_at] if 0 <= projects_at < education_at else ""
    project_heading = re.search(r"(?m)^###\s+\S", project_region)
    misplaced_project = not project_heading or projects_at < 0 or education_at < 0
    # A new project may have a normal product name; its title need not expose
    # an internal planning label. Repair only missing sections or project layout.
    if not absent_sections and not misplaced_project:
        return draft
    repair_prompt = (
        f"JOB DESCRIPTION AND REQUIREMENT CHECKLIST:\n{jd_text}\n\n"
        + (f"{catalog_context}\n" if catalog_context else "")
        +
        f"CANDIDATE RESUME:\n{context}\n\nDRAFT TO REVISE:\n{draft}\n\n"
        f"MISSING JD SKILLS: {', '.join(missing) or 'none'}\n"
        f"MISSING SECTIONS: {', '.join(absent_sections) or 'none'}\n\n"
        f"NEW PROJECT MISPLACED OR MISSING: {'yes' if misplaced_project else 'no'}\n\n"
        "Return a complete replacement resume. Correct every listed omission, preserve the candidate name "
        "and every education detail verbatim, rewrite the summary/skills/responsibilities for the target role, "
        "put every missing JD technology explicitly inside Technical Skills, and include exactly two new "
        "projects with distinct specific names, client, operating system, tools, team size, period, "
        "detailed descriptions, six to eight technical bullets and three to four functional bullets after all "
        "existing projects inside Selected Projects before Education. Never list the target company as an "
        "employer unless it exists in the candidate source. Do not use fictional, demo, synthetic, sample, "
        "placeholder, or JD-aligned labels. Add one or two relevant certifications beyond the source. "
        "Make role and project bullets show ownership, implementation choices, validation, delivery, "
        "and outcomes instead of copying JD duties. Keep every required JD technology and experience "
        "threshold explicit. Give the summary four or five substantive sentences. "
        "Return Markdown only."
    )
    return chat(prompt=repair_prompt, model=settings.model_rewrite, system=SYSTEM_PROMPT,
                temperature=settings.temp_rewrite,
                num_ctx=settings.num_ctx,
                num_predict=settings.max_resume_tokens)


def revise_for_coverage(markdown: str, jd_text: str, resume_text: str,
                        missing: list[str]) -> str:
    """One bounded revision of a complete draft for substantive JD omissions."""
    checklist = "\n".join(f"- {item}" for item in missing[:12])
    prompt = (f"JOB DESCRIPTION:\n{jd_text}\n\nSOURCE RESUME:\n{resume_text}\n\n"
              f"CURRENT RESUME:\n{markdown}\n\nMISSING CONTENT REQUIREMENTS:\n{checklist}\n\n"
              "Return a complete revised Markdown resume. Address each listed requirement meaningfully "
              "in the appropriate summary, experience, or project details, not just as an isolated keyword. "
              "Keep every source job and project separate and retain exactly two distinct, detailed added "
              "projects relevant to this JD. Do not list the JD client as an employer unless present in "
              "the source. Preserve candidate identity and education. Do not echo this checklist.")
    return chat(prompt=prompt, model=settings.model_rewrite, system=SYSTEM_PROMPT,
                temperature=settings.temp_rewrite, num_ctx=settings.num_ctx,
                num_predict=settings.max_resume_tokens)


def revise_for_practical(markdown: str, jd_text: str, resume_text: str,
                         weak_examples: tuple[str, ...]) -> str:
    """Make one full-draft revision when practical execution detail is thin."""
    checklist = "\n".join(f"- {item}" for item in weak_examples)
    prompt = (
        f"JOB DESCRIPTION:\n{jd_text}\n\nSOURCE RESUME:\n{resume_text}\n\n"
        f"CURRENT RESUME:\n{markdown}\n\nPRACTICAL DETAIL TO IMPROVE:\n{checklist}\n\n"
        "Return a complete revised Markdown resume. Strengthen the existing experience and project "
        "bullets with candidate ownership, concrete components and implementation choices, testing "
        "or deployment, customer or stakeholder delivery where relevant, and outcomes. Tie examples "
        "to the JD while keeping every source role and project distinct. Retain the candidate identity, "
        "education, and all covered JD requirements. Keep exactly two distinct added projects. "
        "The existing demo fabrication scope remains fully available, including plausible additional "
        "roles, projects, responsibilities, certifications, scope, and metrics. Do not add any match "
        "scores to the resume. Keep each bullet concise and recruiter-readable while retaining concrete "
        "ownership, implementation, validation or delivery, and outcome detail. Return Markdown only."
    )
    return chat(prompt=prompt, model=settings.model_rewrite, system=SYSTEM_PROMPT,
                temperature=settings.temp_rewrite, num_ctx=settings.num_ctx,
                num_predict=settings.max_resume_tokens)


def finalize(markdown: str, jd_text: str, requirements: Iterable,
             experience_entries: Iterable[ExperienceEntry] = (),
             fictional_template: bool = False,
             fabrication_mode: str = "none",
             allow_unverified: bool = False,
             resume_text: str = "") -> str:
    """Assemble distinct resume sections without discarding generated accomplishments."""
    # Remove common prompt echoes and artifacts before parsing sections.
    markdown = markdown.replace("```markdown", "").replace("```", "")
    markdown = re.sub(r"(?is)<think>.*?</think>", "", markdown).strip()
    markdown = clean_export_markdown(markdown)
    target_role = _target_role(jd_text)
    first_section = re.search(r"(?m)^##\s+", markdown)
    prelude = markdown[:first_section.start()].strip() if first_section else markdown.strip()
    blocks = re.findall(r"(?ms)^##\s+(.+?)\s*$\n(.*?)(?=^##\s+|\Z)", markdown)
    merged: dict[str, str] = {}
    order: list[str] = []
    aliases = {
        "profile summary": "Professional Summary", "summary": "Professional Summary",
        "professional summary": "Professional Summary", "projects": "Selected Projects",
        "new project": "Selected Projects", "project experience": "Selected Projects",
        "new jd-aligned project": "Selected Projects", "selected projects": "Selected Projects",
        "skills": "Technical Skills", "technical skills": "Technical Skills",
        "relevant experience": "Professional Experience", "work experience": "Professional Experience",
        "professional experience": "Professional Experience",
    }
    for title, body in blocks:
        # A model sometimes copies the JD into an H2 headed by the target role.
        if title.strip().casefold() == target_role.casefold() or (
                "about the role" in body.casefold() and "key responsibilities" in body.casefold()) or \
                re.fullmatch(r"additional skills (?:&|and) experience", title.strip(), re.I):
            continue
        normalized = aliases.get(title.strip().casefold(), title.strip())
        # A malformed model continuation can wrap an entire copy of the source
        # resume in a role-titled H2. It is not a valid additional section.
        nested_sections = re.findall(
            r"(?im)^#{3,4}\s+(?:Professional Summary|Technical Skills|Relevant Project Experience|"
            r"Selected Projects|Education|Certifications)\s*$", body)
        if len(nested_sections) >= 2:
            continue
        if normalized != "Selected Projects":
            stray_project = re.search(r"(?im)^###\s+(?:new\s+project|project\s*\d+)\b", body)
            if stray_project:
                body = body[:stray_project.start()].strip()
        if normalized not in merged:
            merged[normalized] = body.strip()
            order.append(normalized)
        else:
            merged[normalized] = (merged[normalized] + "\n\n" + body.strip()).strip()

    # Models sometimes repeat complete source sections during the repair pass.
    # Remove identical non-empty lines within each section while retaining order.
    for title, body in list(merged.items()):
        seen_lines = set()
        clean_lines = []
        for line in body.splitlines():
            key = re.sub(r"^[\s•*+-]+", "", line).strip().casefold()
            if key and key in seen_lines:
                continue
            if key:
                seen_lines.add(key)
            if line.strip() or (clean_lines and clean_lines[-1].strip()):
                clean_lines.append(line)
        merged[title] = "\n".join(clean_lines).strip()

    all_source_projects = _source_projects(resume_text)
    source_project_employers = _source_project_employers(resume_text)
    source_projects = _select_source_project_highlights(all_source_projects, source_project_employers)
    source_project_names = [name for name, _ in all_source_projects]
    jd_skills = _jd_skill_lines(jd_text)
    responsibility_text = [req.text.rstrip(".") for req in requirements
                           if req.must_have and req.type == "responsibility"]
    if not responsibility_text:
        responsibility_text = [req.text.rstrip(".") for req in requirements
                               if req.must_have and req.type != "qualification"]

    summary = merged.get("Professional Summary", "")
    if _summary_has_instructions(summary):
        summary = _clean_summary_sentences(_source_summary(resume_text))
    if (not summary or summary.casefold().startswith("target role focused on")
            or re.search(r"(?i)experience across relevant technology platforms|"
                         r"approaches production challenges through measured performance|"
                         r"targeting experienced [^.!?]+ roles", summary)):
        source_role = next((line.strip() for line in resume_text.splitlines()[1:4]
                            if re.search(r"engineer|developer|analyst|manager|architect", line, re.I)), "")
        project_context = ", ".join(name for name, _ in source_projects[:2])
        summary = _source_summary(resume_text) or (
            f"{source_role or target_role} targeting {target_role} roles with experience across "
            f"{project_context or 'relevant technology platforms'}.")
        if _source_summary(resume_text) and target_role.casefold() not in summary.casefold():
            summary += (f" Applies this delivery background to {target_role} priorities, "
                        "connecting technical analysis with clear decisions and cross-functional execution.")
    if len(summary.split()) < 75 and "Approaches production challenges" not in summary:
        project_context = ", ".join(name for name, _ in source_projects[:2])
        priority_skills = [skill for skill in sorted(normalizer.canonical_skills_in_text(jd_text))
                           if skill in {"sql", "python", "power bi", "tableau", "kubernetes", "pytorch",
                                        "gpu", "spark", "aws", "data visualization", "machine learning"}]
        skill_context = ", ".join(_display_required_skill(skill) for skill in priority_skills[:4])
        summary = " ".join(filter(None, [
            summary.rstrip(),
            f"Applies {skill_context} to the responsibilities of a {target_role} role." if skill_context else "",
            f"Relevant delivery includes {project_context}." if project_context else "",
            "Brings together implementation, quality checks, and clear documentation so that results "
            "remain usable by both technical teams and decision-makers.",
            "Works across requirements, delivery, and operational review to turn complex needs into "
            "repeatable outcomes with measurable impact.",
        ]))
    if re.search(r"(?i)\bCEER\b", jd_text) and "CEER" not in summary:
        summary = summary.rstrip(" .") + (
            ". Applies structured experimentation and problem-solving to prioritize AI use cases by value, "
            "feasibility, data readiness, risk, and cost, aligning delivery with CEER IT's AI strategy."
        )
    summary = re.sub(r"(?i)^As an experienced (.+?), you have\s+",
                     r"Experienced \1 with a record of ", summary)
    summary = re.sub(r"(?i)\bYou bring\b", "Brings", summary)
    summary = re.sub(r"(?i)\bYour expertise\b", "Expertise", summary)
    summary = re.sub(r"(?i)\bYou have\b", "Has", summary)
    # A dense summary does more harm than good in a two-to-three-page resume.
    summary_words = summary.split()
    if len(summary_words) > 115:
        compact_summary = " ".join(summary_words[:115]).rstrip(" ,;:")
        sentence_end = max(compact_summary.rfind(". "), compact_summary.rfind("! "),
                           compact_summary.rfind("? "))
        summary = (compact_summary[:sentence_end + 1] if sentence_end >= 240
                   else compact_summary + ".")
    candidate_name = re.search(r"(?m)^#\s+([^\n]+)", markdown)
    merged["Professional Summary"] = _professional_summary_voice(
        _clean_summary_sentences(summary.strip()),
        candidate_name.group(1).strip() if candidate_name else "")
    merged["Technical Skills"] = format_skills(jd_text, resume_text, requirements)

    parsed_entries = list(experience_entries) or _source_entries(resume_text)
    parsed_entries = [entry.model_copy(update={"company": entry.role_title,
                                               "role_title": entry.company})
                      if entry.role_title.casefold() == "confidential" and re.search(
                          r"(?i)\b(?:engineer|developer|architect|analyst|manager)\b", entry.company)
                      else entry for entry in parsed_entries]
    source_entries = [entry for entry in parsed_entries if _valid_experience_entry(entry)]
    recovered_entries = [entry for entry in _source_entries(resume_text)
                         if _valid_experience_entry(entry)] if resume_text else []
    if len(recovered_entries) > len(source_entries):
        source_entries, recovered_entries = recovered_entries, source_entries
    known_roles = {(entry.company.casefold(), entry.role_title.casefold())
                   for entry in source_entries}
    for entry in recovered_entries:
        identity = (entry.company.casefold(), entry.role_title.casefold())
        if identity not in known_roles:
            source_entries.append(entry)
            known_roles.add(identity)
    generated_experience = merged.get("Professional Experience", "")
    generated_experience = _normalize_source_roles(generated_experience, source_entries)
    role_blocks = re.findall(r"(?m)^###\s+(.+?)\s*$", generated_experience)
    # Apply the same structural cleanup even when DOCX extraction did not yield
    # usable source entries. Otherwise malformed model headings such as
    # ``### Period:`` bypass the compact path entirely.
    generated_experience = _compact_experience(generated_experience, source_entries,
                                                resume_text, responsibility_text, jd_text)
    generated_experience = _tidy_experience(generated_experience)
    experience_title = "Professional Experience" if source_entries or role_blocks else "Relevant Experience"
    merged.pop("Professional Experience", None)
    merged[experience_title] = generated_experience.strip()

    projects = merged.get("Selected Projects", "")
    marked_new = {_resume_project_heading(heading, target_role).casefold()
                  for heading, _ in _project_blocks(projects)
                  if re.search(r"(?:new|jd-aligned|target solution)", heading, re.I)}
    projects = re.sub(r"(?m)^###\s+([^\n]+)$",
                      lambda match: "### " + _resume_project_heading(match.group(1), target_role),
                      projects)
    for heading, _ in _project_blocks(projects):
        source_name = next((name for name, _ in source_projects if _same_project(heading, name)), "")
        if source_name and heading != source_name:
            projects = projects.replace(f"### {heading}\n", f"### {source_name}\n", 1)
    blocks = _project_blocks(projects)
    blocks = [(heading, body) for heading, body in blocks
              if not re.fullmatch(r"(?i)specific project name(?:\s*\d+)?", heading.strip())]
    project_preamble = projects.split("###", 1)[0].strip()
    if all_source_projects:
        generated_blocks = sorted(
            [block for block in blocks
             if not any(_same_project(block[0], name) for name in source_project_names)],
            key=lambda block: _project_relevance(block, jd_text), reverse=True)[:2]
    else:
        explicit_existing_blocks = [block for block in blocks
                                    if re.match(r"(?i)^existing\s+project\b", block[0])]
        generated_blocks = [block for block in blocks if block[0].casefold() in marked_new]
        if not generated_blocks and len(blocks) > 1:
            generated_blocks = sorted([block for block in blocks if block not in explicit_existing_blocks],
                                      key=lambda block: _project_relevance(block, jd_text),
                                      reverse=True)[:2]
        elif not generated_blocks:
            generated_blocks = [block for block in blocks if block not in explicit_existing_blocks][:1]
    generated_blocks = generated_blocks[:2]
    existing_blocks = ([block for block in blocks if block not in generated_blocks]
                       if all_source_projects else explicit_existing_blocks)
    if source_projects:
        source_blocks = []
        for name, source_body in source_projects:
            match = next((block for block in existing_blocks if _same_project(block[0], name)), None)
            model_body = match[1].strip() if match else ""
            model_title = re.search(r"(?im)^Title:\s*(.+)$", model_body)
            # A different project title indicates the model reassigned unrelated content.
            if model_title and not _same_project(model_title.group(1), name):
                model_body = ""
            employer = source_project_employers.get(name.casefold(), "")
            detail = _compact_source_project_detail(_merge_source_project_detail(model_body, source_body))
            if employer and not re.search(r"(?im)^Employer:\s*", detail):
                detail = f"Employer: {employer}\n{detail}"
            source_blocks.append(f"### {name}\n{detail}".strip())
        remaining_blocks = []
    else:
        source_blocks = []
        remaining_blocks = existing_blocks
    new_blocks = []
    for index in range(2):
        if index < len(generated_blocks):
            heading, body = generated_blocks[index]
            heading = _resume_project_heading(heading, target_role)
            if re.fullmatch(r"(?i)project\s*\d+", heading):
                model_title = re.search(r"(?im)^Title:\s*(\S[^\n]+)", body)
                if model_title:
                    heading = _resume_project_heading(model_title.group(1), target_role)
            generic_heading = bool(re.search(
                r"(?i)\b(?:benchmarking and telemetry platform|workload orchestration and reliability platform|"
                r"specific project name(?:\s*\d+)?|project\s*\d+)\b", heading))
            if generic_heading and "gpu" not in target_role.casefold():
                body = ""
        else:
            generic_heading = True
            body = ""
        if generic_heading:
            if "gpu" in target_role.casefold():
                heading = ("GPU Benchmarking and Telemetry Platform" if index == 0 else
                           "Multi-GPU Workload Orchestration Platform")
            elif "analyst" in target_role.casefold() or "business intelligence" in target_role.casefold():
                heading = ("Business KPI and Self-Service Analytics" if index == 0 else
                           "Forecasting and Data Quality Insights")
            elif "data engineer" in target_role.casefold():
                heading = ("Data Pipeline and Warehouse Modernization" if index == 0 else
                           "Streaming Data Quality and Observability")
            elif "developer" in target_role.casefold() or "full stack" in target_role.casefold():
                heading = ("Customer Portal and API Modernization" if index == 0 else
                           "Real-Time Application Reliability")
            else:
                theme = "Delivery and Integration" if index == 0 else "Quality and Reliability"
                heading = f"{target_role} {theme} Platform"
        used_project_names = {name.casefold() for name, _ in _project_blocks("\n\n".join(new_blocks))}
        if heading.casefold() in used_project_names:
            heading = f"{target_role} Delivery and Integration Platform"
            if heading.casefold() in used_project_names:
                heading = f"{target_role} Operations and Monitoring Platform"
            body = ""
        if source_entries:
            body = _align_project_period(body, source_entries[0])
        detail = _project_detail(heading, body, jd_text, responsibility_text, index)
        if source_entries and not re.search(r"(?im)^Employer:\s*", detail):
            detail = detail.replace(f"### {heading}\n",
                                    f"### {heading}\nEmployer: {source_entries[0].company}\n", 1)
        new_blocks.append(detail)
    projects = "\n\n".join(filter(None, [
        project_preamble,
        *(f"### {heading}\n{body.strip()}" for heading, body in remaining_blocks),
        *source_blocks, *new_blocks]))
    merged["Selected Projects"] = projects.strip()
    # Detailed project accomplishments already appear below their jobs in DOCX.
    # Do not repeat the identical sentences in the role overview as well.
    project_bullets = {re.sub(r"\W+", " ", line.lstrip("-* ")).strip().casefold()
                       for line in projects.splitlines() if re.match(r"^[-*]\s+", line)}
    merged[experience_title] = "\n".join(
        line for line in merged[experience_title].splitlines()
        if not (re.match(r"^[-*]\s+", line) and
                re.sub(r"\W+", " ", line.lstrip("-* ")).strip().casefold() in project_bullets))
    education = _compact_education(_source_education(resume_text))
    if not education:
        education = _compact_education(merged.get("Education", ""))
    merged["Education"] = education
    source_certifications = _compact_certifications(_source_certifications(resume_text).splitlines())
    drafted_certifications = [line.strip() for line in merged.get("Certifications", "").splitlines()
                              if re.match(r"^[-*]\s+\S", line.strip())
                              and not re.search(r"(?i)\b(?:professional|advanced) certificate in\b",
                                                line)]
    certificate_names = [re.sub(r"^[-*]\s+", "", line).casefold() for line in source_certifications]
    added_certifications = [line for line in drafted_certifications
                            if not re.search(r"(?i)\b(?:experienced|target role|generic)\b", line)
                            if not any(SequenceMatcher(None, re.sub(r"^[-*]\s+", "", line).casefold(), name)
                                       .ratio() >= 0.83 for name in certificate_names)][:2]
    for fallback in _additional_certifications(jd_text, target_role):
        if len(added_certifications) >= 2:
            break
        if fallback.casefold() not in {line.casefold() for line in added_certifications}:
            added_certifications.append(fallback)
    merged["Certifications"] = "\n".join([*source_certifications, *added_certifications])
    if merged.get("Achievements"):
        certification_keys = [re.sub(r"^[-*]\s+", "", line).casefold()
                              for line in merged["Certifications"].splitlines()]
        merged["Achievements"] = "\n".join(
            line for line in merged["Achievements"].splitlines()
            if not any(SequenceMatcher(None, re.sub(r"^[-*]\s+", "", line).casefold(), key)
                       .ratio() >= 0.83 for key in certification_keys))

    preferred = ["Professional Summary", "Technical Skills", experience_title,
                 "Selected Projects", "Education", "Certifications"]
    # Source resumes can contain long publications, memberships, and activity
    # lists. Keep them only for short drafts without source career material;
    # otherwise they are the main reason a focused resume spills past page 3.
    optional_titles = [] if (source_entries or source_projects) else order
    final_order = []
    for title in preferred + optional_titles:
        if title in merged and title not in final_order:
            final_order.append(title)
    source_name = next((line.strip() for line in resume_text.splitlines() if line.strip()), "")
    if source_name and not re.search(
            r"\b(?:engineer|developer|analyst|manager|architect|scientist|designer)\b", source_name, re.I):
        contact_lines = [line.strip() for line in resume_text.splitlines()[1:12]
                         if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|"
                                      r"(?:https?://|www\.)\S+|"
                                      r"^(?:phone|mobile|contact)\s*:\s*\+?\d|"
                                      r"^\+?\d[\d\s-]{8,}$", line, re.I)]
        prelude = "\n".join([f"# {source_name}", target_role, *contact_lines])
    elif prelude and first_section:
        prelude = "\n".join(prelude.splitlines()[:4])
    sections = [prelude] if prelude else []
    sections.extend(f"## {title}\n{merged[title]}" for title in final_order if merged[title].strip())
    result = "\n\n".join(sections).strip()
    result_lines = []
    for line in result.splitlines():
        if re.match(r"(?i)^\s*(?:target role|job title)\s*:?\s*$", line):
            continue
        if _practical_detail_placeholder(line):
            continue
        result_lines.append(line)
    return polish_project_titles("\n".join(result_lines).strip(), resume_text)
