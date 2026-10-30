"""Versioned, reviewed technology vocabulary; never candidate evidence."""

from __future__ import annotations

import argparse
import json
import re
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path

import yaml

from config import settings


CATALOG_PATH = settings.resources / "technology_catalog.yaml"
BASE_PATH = settings.resources / "technology_catalog_base.json"
BASE_CATEGORIES = {
    "Programming Language": "Programming & APIs",
    "Web Frontend": "Web & Applications", "Web Backend": "Web & Applications",
    "Data & Analytics": "Data Engineering & Warehousing",
    "Database": "SQL & Databases", "Machine Learning & AI": "ML & AI",
    "LLM & GenAI": "ML & AI", "Cloud & DevOps": "Cloud & Infrastructure",
    "Business Software": "Business Platforms & Architecture",
    "Embedded & Hardware": "GPU & Systems", "Legacy Tech": "Tools & Platforms",
    "Security": "Quality & Governance", "Testing & QA": "Quality & Governance",
    "Mobile": "Web & Applications", "Design & Product": "Web & Applications",
}


def surface_key(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().strip())


@lru_cache(maxsize=1)
def snapshot() -> dict:
    data = yaml.safe_load(CATALOG_PATH.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("entries"), list):
        raise ValueError("technology catalog must contain an entries list")
    base = json.loads(BASE_PATH.read_text(encoding="utf-8"))
    reviewed_names = {surface_key(entry["name"]) for entry in data["entries"]}
    for item in base:
        if surface_key(item["skill"]) in reviewed_names:
            continue
        data["entries"].append({
            "name": item["skill"], "aliases": item.get("aliases", []),
            "category": BASE_CATEGORIES.get(item.get("category"), "Tools & Platforms"),
            "description": item.get("description", ""), "source": None,
            "reviewed": None, "baseline": True,
        })
    return data


def surfaces(entry: dict) -> list[str]:
    return [entry["name"], *(entry.get("aliases") or [])]


@lru_cache(maxsize=1)
def surface_index() -> dict[str, dict]:
    index = {}
    for entry in snapshot()["entries"]:
        for form in surfaces(entry):
            index.setdefault(surface_key(form), entry)
    return index


def entry_for(term: str) -> dict | None:
    return surface_index().get(surface_key(term))


def matches(text: str) -> list[dict]:
    """Return distinct, explicitly named JD technologies in first-mention order."""
    hits = []
    for form, entry in surface_index().items():
        if not form or not entry.get("source") or not entry.get("reviewed"):
            continue
        match = re.search(rf"(?<![\w+#]){re.escape(form)}(?![\w+#])", text, re.I)
        if match:
            hits.append((match.start(), -len(form), entry))
    hits.sort(key=lambda item: (item[0], item[1]))
    result, seen = [], set()
    for _, _, entry in hits:
        key = surface_key(entry["name"])
        if key not in seen:
            result.append(entry)
            seen.add(key)
    return result


def context_for_jd(jd_text: str, max_chars: int = 1000) -> str:
    """Small, bounded terminology context; not evidence of candidate experience."""
    header = "TECHNOLOGY REFERENCE (terminology only; not candidate evidence):\n"
    lines = []
    used = len(header)
    for entry in matches(jd_text):
        if not entry.get("source") or not entry.get("reviewed"):
            continue
        line = f"- {entry['name']}: {entry['description']}\n"
        if used + len(line) > max_chars:
            break
        lines.append(line)
        used += len(line)
    return header + "".join(lines) if lines else ""


def audit(jd_text: str = "", today: date | None = None) -> dict:
    """Report catalog maintenance issues without modifying its contents."""
    data = snapshot()
    today = today or date.today()
    seen = {}
    duplicates, unverified, stale = [], [], []
    for entry in data["entries"]:
        name = entry.get("name", "<unnamed>")
        for form in surfaces(entry) if entry.get("name") else []:
            key = surface_key(form)
            if key in seen and seen[key] != name:
                duplicates.append({"surface": form, "owners": [seen[key], name]})
            seen.setdefault(key, name)
        if not entry.get("source") or not entry.get("reviewed") or not entry.get("description"):
            unverified.append(name)
        else:
            reviewed = date.fromisoformat(str(entry["reviewed"]))
            if reviewed + timedelta(days=int(data.get("review_interval_days", 180))) < today:
                stale.append(name)
    # Existing aliases remain authoritative; report disagreements separately.
    from matching import normalizer
    conflicts = []
    for entry in data["entries"]:
        target = normalizer.clean(entry["name"])
        for form in surfaces(entry):
            existing = normalizer.existing_alias(form)
            if existing and existing != target:
                conflicts.append({"surface": form, "existing": existing, "catalog": target})
    missing = sorted(term for term in normalizer.technology_terms_in_text(jd_text)
                     if not entry_for(term) and not any(
                         entry_for(form) for form in normalizer.expand(term))) if jd_text else []
    return {"version": str(data.get("version")), "entries": len(data["entries"]),
            "duplicates": duplicates, "alias_conflicts": conflicts,
            "unverified": unverified, "stale": stale, "jd_terms_without_catalog_entry": missing}


if __name__ == "__main__":
    import json

    parser = argparse.ArgumentParser(description="Audit the versioned technology catalog")
    parser.add_argument("--jd", type=Path, help="Optional JD .txt or .docx to report missing terms")
    args = parser.parse_args()
    jd_text = ""
    if args.jd:
        if args.jd.suffix.casefold() == ".docx":
            from docx import Document
            jd_text = "\n".join(p.text for p in Document(args.jd).paragraphs)
        else:
            jd_text = args.jd.read_text(encoding="utf-8")
    print(json.dumps(audit(jd_text), indent=2))
