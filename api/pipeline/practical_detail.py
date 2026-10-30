"""Internal checks for concrete experience and project descriptions."""

import re
from difflib import SequenceMatcher
from dataclasses import dataclass


_ACTION = re.compile(
    r"^(?:built|designed|implemented|developed|integrated|deployed|delivered|"
    r"automated|migrated|optimized|led|owned|launched|configured|created|architected|engineered|"
    r"validated|tested|monitored|resolved|investigated|negotiated|analyzed|"
    r"established|scaled|orchestrated|standardized|partnered|coordinated|"
    r"translated|shipped|improved|reduced|increased)\b", re.I)
_MECHANISM = re.compile(
    r"\b(?:api|endpoint|service|model|pipeline|workflow|dashboard|database|"
    r"schema|query|integration|architecture|component|"
    r"deployment|release|test|telemetry|monitoring|configuration|"
    r"dataset|contract|account|customer|client|forecast|metric|kpi|"
    r"prototype|infrastructure|interface|migration|"
    r"experiment|acceptance criteria)s?\b", re.I)
_DELIVERY = re.compile(
    r"\b(?:test(?:ed|ing|s)?|validat(?:ed|ion)|deploy(?:ed|ment)?|"
    r"release(?:d)?|rollout|rolled out|production|monitor(?:ed|ing)?|"
    r"incident|handover|support(?:ed)?|customer|client|stakeholder|"
    r"review(?:ed)?|feedback|acceptance|integration|operational|"
    r"troubleshoot(?:ing|ed)?|reliability)\b", re.I)
_RESULT = re.compile(
    r"\b(?:improv(?:ed|ing|ement)|reduc(?:ed|ing|tion)|increas(?:ed|ing)|"
    r"accelerat(?:ed|ing)|saved|enabled|delivered|launched|adopt(?:ed|ion)|"
    r"reliab(?:le|ility)|accurac(?:y|ies)|throughput|latency|conversion|"
    r"quality|impact|outcome|result|uptime|efficien(?:cy|cies)|coverage)\b|\d+%", re.I)
_GENERIC = re.compile(
    r"\b(?:target role|core requirements|relevant technologies|"
    r"cross-functional stakeholders|repeatable outcomes|"
    r"key operating assumptions|distinct part of the target role)\b", re.I)
_PLACEHOLDER = re.compile(
    r"(?i)\b(?:target role|address (?:ai agent )?ownership|add jd-aligned|"
    r"please update|add responsibilities|specific project name|distinct part of the target role)\b|"
    r"\[(?:update|add|insert|mm/yyyy|candidate|company)[^\]]*\]"
)
_GENERIC_PROJECT = re.compile(
    r"(?i)\b(?:delivery and integration platform|quality and reliability platform|"
    r"repeatable execution, measurable quality checks, and documented operations)\b"
)


def bullet_strength(line: str) -> int:
    """Rank details without changing claims or imposing a fabrication policy."""
    text = re.sub(r"^\s*[-*]\s+", "", line).strip()
    if not text:
        return 0
    strength = (2 * bool(_ACTION.search(text)) + 2 * bool(_MECHANISM.search(text))
                + bool(_DELIVERY.search(text)) + bool(_RESULT.search(text))
                + bool(len(text.split()) >= 12) - 2 * bool(_GENERIC.search(text)))
    return max(0, strength)


def strongest_bullets(lines: list[str], limit: int) -> list[str]:
    """Keep the most concrete bullets, preserving order among equal-quality lines."""
    ranked = sorted(enumerate(lines), key=lambda item: (-bullet_strength(item[1]), item[0]))
    return [line for _, line in ranked[:limit]]


def _section(markdown: str, title: str) -> str:
    match = re.search(rf"(?ims)^##\s+{title}\s*$\n(.*?)(?=^##\s+|\Z)", markdown)
    return match.group(1) if match else ""


def _blocks(section: str) -> list[tuple[str, list[str]]]:
    return [(heading.strip(), [line.strip() for line in body.splitlines()
                               if re.match(r"^\s*[-*]\s+", line)])
            for heading, body in re.findall(
                r"(?ms)^###\s+(.+?)\s*$\n(.*?)(?=^###\s+|\Z)", section)]


@dataclass(frozen=True)
class PracticalDetail:
    needs_revision: bool
    quality: tuple[int, int, int, int]
    weak_examples: tuple[str, ...]
    critical_defects: tuple[str, ...] = ()


def _copied_jd_duty(bullet: str, jd_text: str) -> bool:
    normalize = lambda value: " ".join(re.findall(r"[a-z0-9+#.]+", value.casefold()))
    candidate = normalize(re.sub(r"^\s*[-*]\s+", "", bullet))
    if len(candidate.split()) < 6:
        return False
    for line in jd_text.splitlines():
        for sentence in re.split(r"(?<=[.!?])\s+|\s*;\s*", line):
            source = normalize(re.sub(r"^\s*[-*#>]+\s*", "", sentence))
            if len(source.split()) >= 6 and SequenceMatcher(None, candidate, source).ratio() >= 0.9:
                return True
    return False


def assess(markdown: str, jd_text: str = "") -> PracticalDetail:
    """Check whether existing role and project bullets demonstrate execution."""
    experience = _section(markdown, r"(?:Professional|Relevant|Work) Experience")
    projects = _section(markdown, r"(?:Selected|Relevant|Key) Projects")
    role_blocks = _blocks(experience)
    project_blocks = _blocks(projects)
    role_bullets = [line for _, bullets in role_blocks for line in bullets]
    project_bullets = [line for _, bullets in project_blocks for line in bullets]
    defects = []
    if _PLACEHOLDER.search(markdown):
        defects.append("placeholder or copied-duty text remains in the resume")
    if any(_GENERIC_PROJECT.search(heading) for heading, _ in project_blocks):
        defects.append("a generated project still has a generic title")
    if _GENERIC_PROJECT.search(projects):
        defects.append("a generated project still has a generic description")
    if jd_text and any(_copied_jd_duty(line, jd_text)
                       for line in role_bullets + project_bullets):
        defects.append("a role or project bullet copies a JD duty instead of showing delivery")
    reversed_roles = [heading for heading, _ in role_blocks
                      if "confidential" in heading.casefold()
                      and re.search(r"(?i)\b(?:engineer|developer|architect|analyst|manager)\b",
                                    heading.split("|", 1)[0])
                      and re.search(r"(?i)\b(?:engineer|developer|architect|analyst|manager)\b",
                                    heading.split("|", 1)[-1])]
    if reversed_roles:
        defects.append("a source employer and role title appear to be reversed")
    # A sparse or malformed draft should be handled by the existing structural
    # repair path, not by another full-resume model call.
    if len(role_bullets) + len(project_bullets) < 5:
        return PracticalDetail(bool(defects), (-len(defects), 0, 0, 0),
                               tuple(defects), tuple(defects))
    delivered = sum(bool(_DELIVERY.search(line)) for line in role_bullets + project_bullets)
    weak = []
    satisfied = 0
    strong_total = 0
    for label, blocks in (("Experience", role_blocks), ("Project", project_blocks)):
        for heading, bullets in blocks:
            strong = sum(bullet_strength(line) >= 5 for line in bullets)
            strong_total += strong
            needed = 2 if len(bullets) >= 3 else 1
            if strong >= needed:
                satisfied += 1
            elif len(weak) < 6:
                weak.append(f"{label} '{heading[:70]}' needs concrete ownership, implementation, and delivery detail")
    if delivered < 2:
        weak.append("Add testing, deployment, operational, or customer delivery detail")
    quality = (-len(defects), satisfied, strong_total + min(delivered, 3),
               sum(bullet_strength(line) for line in role_bullets + project_bullets))
    return PracticalDetail(bool(weak or defects), quality,
                           tuple([*defects, *weak]), tuple(defects))
