"""Compact, JD-ranked Technical Skills presentation for generated resumes."""

import re
from collections import defaultdict

from matching import normalizer
from matching import technology_catalog
from config import settings


DISPLAY = {
    "salesforce b2b commerce": "Salesforce B2B Commerce",
    "salesforce cpq": "Salesforce CPQ", "salesforce revenue cloud": "Salesforce Revenue Cloud",
    "lightning web components": "Lightning Web Components (LWC)",
    "soap api": "SOAP APIs", "b2b commerce": "B2B Commerce", "apex": "Apex",
    "ab testing": "A/B Testing", "api integration": "API Integration",
    "aws": "AWS", "azure": "Azure", "ci/cd": "CI/CD", "cplusplus": "C++",
    "csharp": "C#", "data visualization": "Data Visualization", "dbt": "dbt",
    "etl": "ETL / ELT", "gcp": "GCP", "golang": "Go", "gpu": "GPU",
    "kpi development": "KPI Development", "power bi dax": "Power BI DAX",
    "lod expressions": "LOD Expressions", "common table expressions (ctes)": "Common Table Expressions (CTEs)",
    "common table expressions ctes": "Common Table Expressions (CTEs)",
    "nvidia data center gpus": "NVIDIA Data Center GPUs",
    "embedded/edge gpus": "Embedded/Edge GPUs", "edge gpus": "Edge GPUs",
    "multi-gpu scaling": "Multi-GPU Scaling", "time-series telemetry": "Time-Series Telemetry",
    "kafka": "Kafka", "llm": "LLMs", "mssql": "SQL Server", "mysql": "MySQL",
    "nodejs": "Node.js", "numpy": "NumPy", "pandas": "Pandas", "apis": "APIs",
    "postgresql": "PostgreSQL", "power bi": "Power BI", "pytorch": "PyTorch",
    "python": "Python", "react": "ReactJS", "redux": "Redux",
    "nestjs": "Nest.js", "socketio": "Socket.io", "rest api": "REST APIs",
    "spark": "Apache Spark", "sql": "SQL", "tensorflow": "TensorFlow",
    "time series": "Time Series Analysis", "typescript": "TypeScript",
}

GROUPS = (
    ("Business Platforms & Architecture", r"salesforce|cpq|revenue cloud|commerce cloud|lightning web|\bapex\b|quote.to.cash|order management|product catalog|pricing|checkout|storefront"),
    ("Enterprise Integration", r"soap|rest api|sap|erp|crm|integration pattern|data migration|data architecture"),
    ("GPU & Systems", r"gpu|cuda|nvml|dcgm|nvidia|nccl|telemetry|benchmark|redfish|ipmi|bmc|linux|memory bandwidth|gemm|embedded|convolution|compute|tensor parallelism|pipeline parallelism|process orchestration|stress testing|dataset generation"),
    ("Analytics & BI", r"power bi|tableau|excel|visualiz|dashboard|kpi|cohort|funnel|retention|customer|product analytics|ab testing|statistics|forecast|time series|reporting|lod expressions|dax|large.scale dataset"),
    ("SQL & Databases", r"\bsql\b|postgres|mysql|oracle|mssql|database|query|window function|subquer|join|aggregation|stored procedure|relational|common table expression|\bcte\b|conditional logic|\bviews\b|performance tuning|data reconciliation"),
    ("Data Engineering & Warehousing", r"etl|elt|spark|kafka|airflow|dbt|warehouse|snowflake|bigquery|redshift|databricks|pandas|numpy|pipeline|data model|data processing|hadoop|flink"),
    ("Programming & APIs", r"python|javascript|typescript|java|golang|csharp|cplusplus|\brust\b|\bapis?\b|graphql|fastapi|flask"),
    ("ML & AI", r"machine learning|deep learning|pytorch|tensorflow|llm|rag|mlops|model evaluation|feature engineering|scikit|hugging face|nlp|computer vision"),
    ("Cloud & Infrastructure", r"\baws\b|\bazure\b|\bgcp\b|cloud|terraform|kubernetes|docker|jenkins|ci/cd|git|security|monitoring|prometheus|grafana|microsoft fabric"),
    ("Web & Applications", r"react|redux|angular|vue|nextjs|nodejs|express|nestjs|socketio|websocket|html|css|frontend|backend|microservices"),
    ("Quality & Governance", r"data quality|data validation|data governance|reconcil|testing|audit|lineage|schema|data cleaning|row.level security"),
)

NON_TECHNICAL = re.compile(
    r"(?i)\b(?:working hours|business acumen|communication|leadership|stakeholder|"
    r"collaboration|problem.solving|mentoring|opportunity recognition|presentation|"
    r"independent project|ambiguous requirement|business recommendation|"
    r"multiple analytical projects|experience working with|documentation standards)\b"
)


def _group(skill: str) -> str | None:
    if "computer vision" in skill.casefold():
        return "ML & AI"
    if "row-level security" in skill.casefold():
        return "Quality & Governance"
    for name, pattern in GROUPS:
        if re.search(pattern, skill, re.I):
            return name
    entry = technology_catalog.entry_for(skill) if settings.catalog_enabled else None
    if entry:
        return entry["category"]
    return None


def _display(skill: str) -> str:
    key = normalizer.canonical(skill)
    if key in DISPLAY:
        return DISPLAY[key]
    entry = technology_catalog.entry_for(skill) if settings.catalog_enabled else None
    if entry:
        return entry["name"]
    acronyms = {"gpu", "gpus", "sql", "api", "apis", "bi", "ml", "ai", "llm", "llms",
                "nvml", "dcgm", "bmc", "ipmi", "gemm", "nccl", "aws", "gcp", "etl", "elt"}
    return " ".join(part.upper() if part.lower() in acronyms else part.capitalize()
                    for part in skill.split())


def _source_skill_text(resume_text: str) -> str:
    match = re.search(r"(?ims)^(?:(?:Core )?(?:Technical )?Skills\s*:?|Technologies\s*\|\s*Tools)\s*$\n(.*?)(?="
                      r"^(?:Education|Professional Experience|Relevant Project Experience|"
                      r"Work Experience|Certifications)\s*:?\s*$|^Degree\s*\||^#?[^\n]+\(\w+[^\n]*\d{4}|\Z)", resume_text)
    return match.group(1) if match else ""


def _source_skill_items(resume_text: str) -> list[tuple[str, str | None]]:
    """Read source skill rows without discarding tools absent from the JD lexicon."""
    items = []
    raw_lines = _source_skill_text(resume_text).splitlines()
    structured = any(re.match(r"^[^|:]{2,48}\s*(?:\||:)\s*\S", line.strip()) for line in raw_lines)
    if not structured:
        labels = re.compile(r"(?i)^(?:technologies|tools|devops|languages|programming|"
                            r"web technologies|databases|cloud|operating systems|code repo|"
                            r"ai\s*/\s*ml exposure|technical skills|core skills|big data|"
                            r"streaming|data science|orchestration\s*&\s*transformation)$")
        joined = []
        buffer = ""
        for raw in raw_lines:
            line = raw.strip()
            if labels.fullmatch(line):
                if buffer and buffer.count("(") <= buffer.count(")"):
                    joined.append(buffer)
                    buffer = ""
                continue
            if line:
                separator = ", " if (buffer and not buffer.endswith(",") and depth_if_balanced(buffer)
                                       and re.match(r"^(?:GCP|AWS|Azure)\s*\(", line)) else " "
                buffer = (buffer + separator + line).strip() if buffer else line
        if buffer:
            joined.append(buffer)
        raw_lines = joined
    for line in raw_lines:
        line = re.sub(r"^\s*[-*•]\s*", "", line).strip()
        if not line:
            continue
        match = re.match(r"^([^|:]{2,48})\s*(?:\||:)\s*(.+)$", line)
        label, value = (match.group(1).strip(), match.group(2).strip()) if match else ("", line)
        if label.casefold() in {"technologies", "category", "skill", "skills"} and value.casefold() in {
                "tools", "technologies", "skills"}:
            continue
        preferred = next((name for name, pattern in (
            ("Analytics & BI", r"\bbi\b|visualiz|analytics|reporting"),
            ("SQL & Databases", r"database"),
            ("Data Engineering & Warehousing", r"big data|streaming|orchestration|transformation|warehouse|data processing"),
            ("Programming & APIs", r"language|programming|api"),
            ("ML & AI", r"machine learning|\bml\b|\bai\b"),
            ("Cloud & Infrastructure", r"cloud|operating system|code repo|devops|infrastructure"),
            ("Web & Applications", r"web|frontend|backend"),
        ) if re.search(pattern, label, re.I)), None)
        start = 0
        depth = 0
        parts = []
        for index, char in enumerate(value):
            depth += (char == "(") - (char == ")")
            if char == "," and depth == 0:
                parts.append(value[start:index])
                start = index + 1
        parts.append(value[start:])
        items.extend((term.strip(" .;"), preferred) for term in parts if term.strip(" .;"))
    return items


def depth_if_balanced(text: str) -> bool:
    return text.count("(") == text.count(")")


def _explicit_jd_terms(jd_text: str) -> list[tuple[str, int]]:
    """Read named technologies from JD skill rows, including Markdown bold rows."""
    found = []
    for match in re.finditer(r"(?m)^\s*(?:[-*]\s*)?(?:\*\*)?([^\n:]{2,48}):(?:\*\*)?\s*([^\n]+)", jd_text):
        label, value = match.group(1).strip(" *"), match.group(2).strip(" *")
        if not re.search(r"(?i)programming|analysis|data|database|warehouse|cloud|integration|"
                         r"version control|bi|visualization|processing|gpu|benchmark|systems|"
                         r"automation|ml|ai|security|tools|technologies|framework", label):
            continue
        for piece in re.split(r",|\s+or\s+|\s+/\s+", value):
            term = piece.strip(" .;*()")
            if term and len(term.split()) <= 4 and not NON_TECHNICAL.search(term):
                found.append((term, match.start()))
    return found


def format_skills(jd_text: str, resume_text: str, requirements) -> str:
    """Prioritize explicit JD skills, then related source technologies; no tables."""
    candidates: dict[str, tuple[str, int, int, str]] = {}

    def add(term: str, rank: int, position: int, *, explicit: bool = False,
            source: bool = False, preferred: str | None = None) -> None:
        key = normalizer.canonical(term)
        if not key or (not source and NON_TECHNICAL.search(key)) or len(key.split()) > (24 if source else 4):
            return
        category = _group(key) or preferred
        if not category and not (explicit or source):
            return
        if not category:
            category = "Tools & Platforms"
        preserve_surface = ((source or explicit) and key not in DISPLAY
                            and not (settings.catalog_enabled and technology_catalog.entry_for(term)))
        display = term.strip() if preserve_surface else _display(term if explicit or source else key)
        old = candidates.get(key)
        if old is None or (rank, position) < (old[1], old[2]):
            candidates[key] = (display, rank, position, category)

    for term, position in _explicit_jd_terms(jd_text):
        add(term, 0, position, explicit=True)
    for term in normalizer.canonical_skills_in_text(jd_text):
        if term == "security" and "row-level security" in jd_text.casefold():
            continue
        if term == "testing" and not re.search(r"(?i)\b(?:unit testing|automated testing|test automation)\b", jd_text):
            continue
        surfaces = normalizer.expand(term)
        position = min((match.start() for surface in surfaces
                        if (match := re.search(r"(?i)(?<!\w)" + re.escape(surface) + r"(?!\w)", jd_text))),
                       default=len(jd_text))
        add(term, 1, position)
    if "row-level security" in jd_text.casefold():
        add("Row-Level Security", 1, jd_text.casefold().find("row-level security"), explicit=True)
    # Requirement extraction can introduce soft skills. Retain only named,
    # technical requirements and unfamiliar tool names with a technical shape.
    for req in requirements:
        if req.type not in {"hard_skill", "tool", "technology", "responsibility"}:
            continue
        for term in set(req.canonical_skills) | normalizer.canonical_skills_in_text(req.text):
            if (term not in normalizer.canonical_skills_in_text(term)
                    and (len(term.split()) > 4 or (req.type != "hard_skill" and
                         not re.search(re.escape(term), jd_text + "\n" + req.text, re.I)))):
                continue
            position = jd_text.casefold().find(term.casefold())
            add(term, 1, position if position >= 0 else len(jd_text))
    advanced_sql = re.search(r"(?ims)^#{0,6}\s*Advanced SQL Requirements\s*$\n(.*?)(?=^#{1,6}\s+|\Z)", jd_text)
    if advanced_sql:
        for line in advanced_sql.group(1).splitlines():
            term = line.strip(" .;*-\t")
            if term and len(term.split()) <= 4 and term.casefold() not in {"strong knowledge of:"}:
                add(term, 1, jd_text.find(line), explicit=True)
    for match in re.finditer(r"(?i)\b(?:knowledge|experience|proficiency|expertise|familiarity)\s+"
                             r"(?:with|of|in)\s+([^.;\n]{1,120})", jd_text):
        for piece in re.split(r",|\band\b|\bor\b", match.group(1), flags=re.I):
            term = piece.strip(" .()[]")
            if term and len(term.split()) <= 3 and re.search(r"[A-Z0-9]|[.#/+]", term):
                add(term, 2, match.start(), explicit=True)
    required_section = False
    for line in jd_text.splitlines():
        stripped = line.strip()
        if re.match(r"(?i)^required (?:technical )?skills\s*:?$", stripped):
            required_section = True
            continue
        if required_section and (not stripped or re.match(r"(?i)^(?:preferred|candidate profile|about)\b", stripped)):
            required_section = False
        if required_section and re.match(r"^[-*•]\s+[A-Za-z][\w.+#/-]{2,40}$", stripped):
            add(re.sub(r"^[-*•]\s+", "", stripped), 1, jd_text.find(stripped), explicit=True)
    for index, (term, preferred) in enumerate(_source_skill_items(resume_text)):
        add(term, 3, index, source=True, preferred=preferred)
    if "salesforce b2b commerce" in candidates:
        candidates.pop("b2b commerce", None)
    grouped = defaultdict(list)
    for display, rank, position, category in candidates.values():
        grouped[category].append((rank, position, display))
    role = jd_text[:300].casefold()
    primary = ("Business Platforms & Architecture" if "salesforce" in role or "commerce" in role else
               "GPU & Systems" if "gpu" in role else
               "Analytics & BI" if "analyst" in role or "business intelligence" in role else
               "Data Engineering & Warehousing" if "data engineer" in role else
               "Web & Applications" if "developer" in role or "full stack" in role else "")
    order = sorted(grouped, key=lambda name: (
        0 if name == primary else 1,
        min((rank, position) for rank, position, _ in grouped[name]),
        next((i for i, (title, _) in enumerate(GROUPS) if title == name), len(GROUPS))))
    return "\n".join(
        f"- **{name}:** " + ", ".join(display for _, _, display in sorted(grouped[name]))
        for name in order if grouped[name]
    )
