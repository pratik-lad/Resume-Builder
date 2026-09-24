"""Build and tailor a candidate resume to the complete job description."""

import re
import calendar
from datetime import date
from typing import Iterable

from config import settings
from llm.client import chat
from matching import normalizer
from schemas import ExperienceEntry


PROMPT_VERSION = "resume-builder-tailoring-v12"
FINALIZER_VERSION = "resume-finalizer-v8"

_DISPLAY_SKILL = {
    "nodejs": "Node.js", "express": "Express.js", "websockets": "WebSockets",
    "mongodb": "MongoDB", "react": "ReactJS", "nextjs": "Next.js",
    "redux": "Redux", "nestjs": "Nest.js", "socketio": "Socket.io",
    "rest api": "REST APIs", "javascript": "JavaScript",
}

_SECTION_ALIASES = {
    "profile summary": "professional summary",
    "summary": "professional summary",
    "professional summary": "professional summary",
    "skills": "technical skills",
    "technical skills": "technical skills",
    "projects": "selected projects",
    "project experience": "selected projects",
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
        r"(?im)^(?:#{1,6}\s*)?(?:missing jd skills|missing sections|"
        r"new project misplaced or missing)\s*:?\s*$|"
        r"^the new project is missing, so i added it\b.*$"
    )
    match = marker.search(markdown)
    return markdown[:match.start()].rstrip() if match else markdown


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


def _fictional_experience_section(target_role: str, responsibilities: list[str]) -> str:
    """Create clearly marked synthetic experience for the demo-only output mode."""
    primary = responsibilities[:3] or [
        "Designed and delivered scalable product capabilities across the development lifecycle",
        "Collaborated with product and engineering stakeholders to deliver reliable customer outcomes",
    ]
    secondary = responsibilities[3:5] or primary[:2]
    primary_bullets = "\n".join(f"- {item}." for item in primary)
    secondary_bullets = "\n".join(f"- {item}." for item in secondary)
    return (
        f"### {target_role} | Fictional Product Systems\n"
        "January 2021 – Present (Fictional demo experience)\n"
        f"{primary_bullets}\n\n"
        f"### {target_role} | Fictional Digital Labs\n"
        "June 2018 – December 2020 (Fictional demo experience)\n"
        f"{secondary_bullets}"
    )

SYSTEM_PROMPT = """You are a high-performance resume builder and job-tailoring engine.
Rebuild the supplied candidate resume into a polished, ATS-readable resume targeted to the complete
job description. The uploaded resume is the candidate foundation, not merely a style reference.

Preserve the candidate's supplied name, contact details, employers, role titles, employment timeline,
all education details (institution, degree, dates, grades), and recognizable project identities. Improve organization, section order, summaries,
skills presentation, project descriptions, and accomplishment bullets. Use strong, concise language
and make the candidate's background clearly relevant to the target role.

Place the target role directly below the candidate name. Do not insert the target role as an additional
employer position. Do not state a JD-required experience duration unless the candidate's supplied dates
support it. Transform the supplied experience and project entries in place: retain one entry per
distinct source job or project, tailor its content to the JD, and do not repeat it in a second section.
Replace the original summary with a target-role summary. Rebuild Technical Skills so JD technologies are
prominent. Rewrite experience/project responsibilities around the JD's duties and production lifecycle.
Add exactly one new substantial JD-aligned project with a distinct name, one-line description, technology
line, and 3-5 strong bullets; it must demonstrate the most important target skills that the source projects
do not cover. Keep existing projects in their original order, and place this new project last inside
Selected Projects before Education. Never claim that the candidate already
works for the target company. If the source has no employment history, use "Relevant Project Experience"
rather than inventing an employer or converting every project into a job.

Cover the complete JD across the resume, including required and preferred skills, technologies,
responsibilities, qualifications, domain knowledge, experience expectations, and soft skills. You may
expand or reshape resume content where needed for comprehensive JD alignment; do not collapse distinct
jobs or projects into one generic bullet list. Preserve every independent job and project under its own
clear Markdown subheading. Before drafting, map every JD requirement to Professional Summary, Technical
Skills, an existing Experience entry, an existing Project, or the one appended JD-aligned Project. Do not
leave a required JD responsibility implied: express it in a specific bullet.

Before returning, perform this silent quality check against the complete inputs:
1. Every explicit JD requirement appears meaningfully in the resume.
2. The candidate name and every supplied college or university name remain verbatim.
3. Experience, skills, and projects are rebuilt for the target role rather than copied mechanically.
4. Independent jobs and projects remain independent sections with their own subheadings.
5. Each top-level section appears once; Experience and Projects are not duplicated under alternate names.
6. The target role is a headline, not a fabricated duplicate employment entry.
7. Existing projects remain ordered and exactly one JD-aligned project is last.
8. Every job date line uses the editable format [MM/YYYY - MM/YYYY or Present].
9. The output contains no missing sections, conversational filler, reasoning, or formatting artifacts.
Correct any failed item before returning. Do not print the checklist or its result.

Use this stable Markdown structure when the information is available:
# Candidate Name
Target Role
Contact details
## Professional Summary
## Technical Skills
## Professional Experience
### Role | Employer
Dates: [MM/YYYY - MM/YYYY or Present]
## Selected Projects
### Project Name
## Education
## Certifications

Return only the completed resume as valid Markdown. Do not add conversational introductions,
explanations, warnings, notes, analysis, code fences, <think> tags, or role labels such as User: or
Assistant:.
Keep the finished resume concise and within approximately two pages; prefer compact, high-signal bullets.

"""


def generate(jd_text: str, resume_text: str = "") -> str:
    context = resume_text.strip()
    prompt = f"JOB DESCRIPTION:\n{jd_text.strip()}"
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
    new_project = re.search(r"(?im)^###\s+.*\b(?:new|jd-aligned)\b.*\bproject\b.*$", draft)
    new_project_at = new_project.start() if new_project else -1
    misplaced_project = new_project_at < 0 or projects_at < 0 or education_at < 0 or not (projects_at < new_project_at < education_at)
    # Technical-skill coverage is deterministically completed by ``finalize``.
    # Do not make a second, slow LLM request just to repeat keywords that the
    # output stage will add anyway.  A repair pass remains for broken sections
    # or a genuinely missing/misplaced project.
    if not absent_sections and not misplaced_project:
        return draft
    repair_prompt = (
        f"JOB DESCRIPTION AND REQUIREMENT CHECKLIST:\n{jd_text}\n\n"
        f"CANDIDATE RESUME:\n{context}\n\nDRAFT TO REVISE:\n{draft}\n\n"
        f"MISSING JD SKILLS: {', '.join(missing) or 'none'}\n"
        f"MISSING SECTIONS: {', '.join(absent_sections) or 'none'}\n\n"
        f"NEW PROJECT MISPLACED OR MISSING: {'yes' if misplaced_project else 'no'}\n\n"
        "Return a complete replacement resume. Correct every listed omission, preserve the candidate name "
        "and every education detail verbatim, rewrite the summary/skills/responsibilities for the target role, "
        "put every missing JD technology explicitly inside Technical Skills, and include exactly one new "
        "JD-aligned project with a name, description, technologies, and responsibility bullets after all "
        "existing projects inside Selected Projects before Education. Never list the target company as an "
        "employer unless it exists in the candidate source. Return Markdown only."
    )
    return chat(prompt=repair_prompt, model=settings.model_rewrite, system=SYSTEM_PROMPT,
                temperature=settings.temp_rewrite,
                num_ctx=settings.num_ctx,
                num_predict=settings.max_resume_tokens)


def finalize(markdown: str, jd_text: str, requirements: Iterable,
             experience_entries: Iterable[ExperienceEntry] = ()) -> str:
    """Enforce ATS structure and full requirement surface after model generation."""
    # Remove common prompt echoes and artifacts before parsing sections.
    markdown = re.split(r"(?im)^Return only the completed resume", markdown, maxsplit=1)[0]
    markdown = markdown.replace("```markdown", "").replace("```", "")
    markdown = re.sub(r"(?is)<think>.*?</think>", "", markdown).strip()
    markdown = _strip_repair_artifacts(markdown)
    first_section = re.search(r"(?m)^##\s+", markdown)
    prelude = markdown[:first_section.start()].strip() if first_section else markdown.strip()
    blocks = re.findall(r"(?ms)^##\s+(.+?)\s*$\n(.*?)(?=^##\s+|\Z)", markdown)
    merged: dict[str, str] = {}
    order: list[str] = []
    aliases = {
        "profile summary": "Professional Summary", "summary": "Professional Summary",
        "professional summary": "Professional Summary", "projects": "Selected Projects",
        "new project": "Selected Projects", "project experience": "Selected Projects",
        "selected projects": "Selected Projects", "technical skills": "Technical Skills",
    }
    for title, body in blocks:
        normalized = aliases.get(title.strip().casefold(), title.strip())
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

    canonical_skills = sorted({skill for req in requirements
                               for skill in (set(req.canonical_skills) |
                                             normalizer.technology_terms_in_text(req.text))})
    display_skills = [_DISPLAY_SKILL.get(skill, skill) for skill in canonical_skills]
    target_stack = ", ".join(display_skills)
    role_match = re.search(
        r"\b(?:as|for)\s+(?:an?\s+)?([A-Z][A-Za-z .+/-]{2,50}?(?:Developer|Engineer|Scientist|Analyst|Manager|Designer))\b",
        jd_text, re.I)
    target_role = role_match.group(1).strip() if role_match else "Target Role"
    responsibility_text = [req.text.rstrip(".") for req in requirements
                           if req.must_have and req.type == "responsibility"]
    if not responsibility_text:
        responsibility_text = [req.text.rstrip(".") for req in requirements if req.must_have]

    merged["Professional Summary"] = (
        f"{target_role} focused on building robust, scalable, and user-friendly products across "
        f"frontend and backend systems. Applies {target_stack or 'modern application technologies'} "
        "to turn concepts into maintainable, tested, production-ready solutions."
    )
    skills_body = merged.get("Technical Skills", "")
    skills_body = "\n".join(line for line in skills_body.splitlines()
                            if not re.match(r"^\s*[-*]?\s*Target Full-Stack Technologies\s*:",
                                            line, re.I))
    unique_skill_lines = []
    seen_skill_lines = set()
    for line in skills_body.splitlines():
        key = re.sub(r"\s+", " ", line).strip().casefold()
        if key and key not in seen_skill_lines:
            seen_skill_lines.add(key)
            unique_skill_lines.append(line)
    skills_body = "\n".join(unique_skill_lines)
    present = normalizer.canonical_skills_in_text(skills_body)
    missing = [skill for skill in canonical_skills if skill not in present]
    skills_body = f"- Target Full-Stack Technologies: {target_stack}\n{skills_body}".strip()
    merged["Technical Skills"] = skills_body

    source_entries = list(experience_entries)
    experience_title = next((title for title in order if "experience" in title.casefold()), None)
    if source_entries:
        # Preserve source identities and editable date fields, but keep the
        # model-generated JD-aligned responsibility bullets.
        generated_experience = merged.get(experience_title or "Professional Experience", "")
        experience_title = "Professional Experience"
        merged[experience_title] = _tailored_experience_section(
            source_entries, generated_experience, responsibility_text)
    elif not experience_title:
        experience_title = "Relevant Experience"
        merged[experience_title] = "\n".join(f"- {item}." for item in responsibility_text)
    projects = merged.get("Selected Projects", "")
    generated_project = re.search(
        r"(?ims)^###\s+.*\b(?:new|jd-aligned)\b.*\bproject\b.*?(?=^###\s+|\Z)", projects)
    if generated_project:
        new_project = generated_project.group(0).strip()
        projects = (projects[:generated_project.start()] + projects[generated_project.end():]).strip()
    else:
        new_project = (
            "### JD-Aligned Project: Target Solution\n"
            "Description: Built to demonstrate the target role's core workflow and delivery requirements.\n"
            f"Technologies: {target_stack}\n" +
            "\n".join(f"- {item}." for item in responsibility_text[:3])
        )
    projects = (projects.rstrip() + "\n\n" + new_project).strip()
    merged["Selected Projects"] = projects.strip()

    preferred = ["Professional Summary", "Technical Skills", experience_title,
                 "Selected Projects", "Education"]
    final_order = []
    for title in preferred + order:
        if title in merged and title not in final_order:
            final_order.append(title)
    sections = [prelude] if prelude else []
    sections.extend(f"## {title}\n{merged[title]}" for title in final_order if merged[title].strip())
    return "\n\n".join(sections).strip()
