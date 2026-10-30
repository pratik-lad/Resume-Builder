"""Final display formatting; does not change generation or source records."""
import re

_MONTH = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\.?"
_YEAR = r"(?:19|20)\d{2}"
_DATE = rf"(?:\d{{1,2}}\s+{_MONTH}\s*,?\s*{_YEAR}|{_MONTH}\s+\d{{1,2}},?\s+{_YEAR}|{_MONTH}\s+{_YEAR}|{_YEAR}[-/]\d{{1,2}}(?:[-/]\d{{1,2}})?|\d{{1,2}}[-/]\d{{1,2}}[-/](?:{_YEAR}|\d{{2}})|\d{{1,2}}[/-]{_YEAR}|{_YEAR})"
_RANGE = re.compile(rf"(?<!\w){_DATE}\s*(?:[-\u2013\u2014]|\bto\b|\bthrough\b)\s*(?:{_DATE}|Present|Current|Ongoing|Now)(?!\w)", re.I)
_FULL_DATE = re.compile(rf"(?<!\w)(?:{_MONTH}\s+(?:\d{{1,2}},?\s+)?{_YEAR}|\d{{1,2}}\s+{_MONTH}\s+{_YEAR}|{_YEAR}[-/]\d{{1,2}}(?:[-/]\d{{1,2}})?|\d{{1,2}}[-/]\d{{1,2}}[-/](?:{_YEAR}|\d{{2}})|\d{{1,2}}[/-]{_YEAR})(?!\w)", re.I)
_CONFIDENTIAL = re.compile(r"\s*#\s*confidential\b", re.I)


def _company_name(value: str) -> str:
    """Return a comparison key without any confidential marker or markdown."""
    clean = value.replace("**", "")
    clean = _CONFIDENTIAL.sub("", clean)
    return re.sub(r"\s+", " ", clean).strip(" |-")


def _company_key(value: str) -> str:
    return re.sub(r"\W+", " ", _company_name(value).casefold()).strip()


def format_resume(markdown: str, source_text: str = "", experience_entries=()) -> str:
    """Hide calendar dates, keep experience durations, and mark added companies."""
    source_titles = [match.group(1).strip().casefold() for match in re.finditer(
        r"(?im)^([^\n|]{3,90}?)\s*\|\s*#?\s*confidential\b", source_text)
        if re.search(r"(?i)\b(?:engineer|developer|analyst|manager|designer|architect|consultant|lead|specialist)\b",
                     match.group(1))]
    if source_titles:
        section = re.search(r"(?ims)^##\s+(?:Professional|Work|Relevant) Experience\s*\n(.*?)(?=^##\s+|\Z)", markdown)
        if section:
            blocks = re.split(r"(?m)(?=^###\s+)", section.group(1))
            kept = []
            for block in blocks:
                heading = re.match(r"(?m)^###\s+([^\n]+)", block)
                if heading and "|" in heading.group(1):
                    left, right = (part.strip().casefold() for part in heading.group(1).split("|", 1))
                    if ("confidential" in left and any(title in right for title in source_titles)):
                        continue
                kept.append(block)
            markdown = (markdown[:section.start(1)] + "".join(kept)
                        + markdown[section.end(1):])
    source_raw = re.sub(r"\s+", " ", source_text)
    source = _company_key(source_raw)
    employers = {_company_key(entry.company) for entry in experience_entries if entry.company}
    marked_employers = {_company_key(entry.company) for entry in experience_entries
                        if entry.company and _CONFIDENTIAL.search(entry.company)}

    def company_label(value: str) -> str:
        value = value.strip()
        name = _company_name(value)
        key = _company_key(name)
        if not name:
            return value
        existing = key in employers or (key and key in source)
        supplied_marker = key in marked_employers or bool(re.search(
            rf"(?i){re.escape(name)}\s*#\s*confidential\b", source_raw))
        # Generated names get one marker; source names keep their supplied
        # marker state. This makes repeated formatting passes idempotent.
        return name + (" #Confidential" if not existing or supplied_marker else "")

    section = ""
    output = []
    for original in markdown.splitlines():
        line = original
        heading = re.match(r"^##\s+(.+)", line)
        if heading:
            section = heading.group(1).casefold()
        # Dates and period fields carry no accomplishments. Duration fields are
        # project metadata; years-of-experience claims elsewhere remain intact.
        if re.match(r"(?i)^\s*(?:[-*]\s+)?(?:\*\*)?(?:dates?|period|duration|employment dates?|date of birth|dob|graduation date|issued|expires|expiry date)(?:\*\*)?\s*:", line):
            continue
        # Protect contact links, email addresses, and version identifiers.
        protected = []
        def protect(match):
            protected.append(match.group())
            return f"\x00{len(protected)-1}\x00"
        line = re.sub(r"https?://\S+|www\.\S+|[\w.+-]+@[\w.-]+", protect, line)
        line = _RANGE.sub("", line)
        line = _FULL_DATE.sub("", line)
        if section in {"education", "certifications", "achievements", "awards"}:
            line = re.sub(rf"(?:\s*[,;|\u2013\u2014-]\s*|\s+){_YEAR}\s*$", "", line)
        if re.fullmatch(r"\s*(?:Present|Current|Ongoing)\s*", line, re.I):
            continue
        # Isolated calendar years in metadata and prose; avoid product versions
        # such as SQL Server 2022 and measurements such as 2024 transactions.
        line = re.sub(rf"(?i)\b(?:since|during|in|from|graduated(?: in)?|issued(?: in)?|expires(?: in)?)\s+{_YEAR}\b", "", line)
        line = re.sub(rf",\s*{_YEAR}(?=\s*[.!?]?\s*$)", "", line)
        line = re.sub(rf"\(\s*{_YEAR}\s*\)|(?<=\|)\s*{_YEAR}\s*(?=\||$)|^\s*{_YEAR}\s*$", "", line)
        line = re.sub(r"\(\s*\)|\[\s*\]", "", line)
        line = re.sub(r"\s+([.,;:!?])", r"\1", line)
        line = re.sub(r"[ \t]{2,}", " ", line).rstrip(" |\u2013\u2014-")
        for index, value in enumerate(protected):
            line = line.replace(f"\x00{index}\x00", value)
        if not line.strip() and original.strip():
            continue
        heading = re.match(r"^##\s+(.+)", line)
        if heading:
            section = heading.group(1).casefold()
        if section in {"professional experience", "work experience", "experience", "employment history", "relevant experience"}:
            role = re.match(r"^(###\s+)(.+)", line)
            if role and "|" in role.group(2):
                parts = role.group(2).split("|")
                parts[1] = " " + company_label(parts[1])
                line = role.group(1) + "|".join(parts)
        field = re.match(r"^(\s*(?:[-*]\s+)?(?:\*\*)?(?:Employer|Company|Client)(?:\*\*)?\s*:\s*)(.+)$", line, re.I)
        if field:
            line = field.group(1) + company_label(field.group(2))
        output.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(output)).strip()
