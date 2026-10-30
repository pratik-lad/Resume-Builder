"""Alias normalisation. 'Postgres', 'postgre sql' and 'PostgreSQL' must become one thing.

This is the boring file that decides how good your matching is.
Grow it from eval failures, not from imagination.
"""
import re
from functools import lru_cache

import yaml

from config import settings
from matching import technology_catalog

_ALIASES: dict[str, list[str]] = yaml.safe_load(
    (settings.resources / "skill_aliases.yaml").read_text(encoding="utf-8")
)
# alias -> canonical, plus canonical -> itself
_MAP: dict[str, str] = {}
for canon, variants in _ALIASES.items():
    _MAP[canon.lower()] = canon.lower()
    for v in variants or []:
        _MAP[str(v).lower()] = canon.lower()
_LEGACY_MAP = dict(_MAP)
_CATALOG_FORMS: dict[str, set[str]] = {}
for entry in technology_catalog.snapshot()["entries"] if settings.catalog_enabled else ():
    canon = entry["name"].casefold()
    forms = {form.casefold() for form in technology_catalog.surfaces(entry)}
    if entry.get("baseline"):
        forms = {form for form in forms if len(form) >= 3}
        if len(canon) < 3:
            continue
    # A pre-existing alias wins. Skip the whole catalog entry if its own name
    # would split into two canonicals (PySpark -> spark is one example).
    if any(_LEGACY_MAP.get(form, canon) != canon for form in forms):
        continue
    for form in forms:
        _MAP.setdefault(form, canon)
    _CATALOG_FORMS.setdefault(canon, set()).update(forms)


def existing_alias(term: str) -> str | None:
    """Canonical mapping before catalog enrichment, for conflict audits."""
    return _LEGACY_MAP.get(term.casefold().strip())

_TECH_CUE = re.compile(r"\b(?:with|using|including|technologies?|tech stack|proficiency in|experience with|skills? required)\s+([^\n.;:]{1,180})", re.I)
_TECH_SHAPE = re.compile(r"(?:[.#/+]|\d|[a-z][A-Z]|^[A-Z]{2,}$)")
_TECH_STOP = {"a", "an", "and", "or", "the", "experience", "development", "software",
              "engineering", "teams", "customers", "business", "technology", "technologies"}


def clean(text: str) -> str:
    t = text.lower().strip()
    t = re.sub(r"[^\w+#./\- ]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


@lru_cache(maxsize=4096)
def canonical(term: str) -> str:
    """Map a raw skill string to its canonical form (or itself, cleaned)."""
    c = clean(term)
    return _MAP.get(c, c)


def expand(canon: str) -> set[str]:
    """Canonical form -> every surface form it may legitimately appear as."""
    c = canon.lower()
    out = {c}
    for v in _ALIASES.get(c, []) or []:
        out.add(str(v).lower())
    out.update(_CATALOG_FORMS.get(c, ()))
    return out


def canonical_set(terms: list[str]) -> set[str]:
    return {canonical(t) for t in terms if t and t.strip()}


def all_surface_forms(canon_terms: set[str]) -> set[str]:
    out: set[str] = set()
    for c in canon_terms:
        out |= expand(c)
    return out


@lru_cache(maxsize=4096)
def _surface_pattern(surface: str):
    # The catalogue exceeds re's small global cache. Retain identical compiled
    # patterns rather than evict/recompile them on every passage; aliases and
    # token boundaries are unchanged for both legacy and desktop callers.
    return re.compile(rf"(?<![\w+#]){re.escape(surface)}(?![\w+#])")


def canonical_skills_in_text(text: str) -> set[str]:
    """Find configured skills in free text while respecting token boundaries."""
    lowered = text.lower()
    found: set[str] = set()
    for surface, canon in _MAP.items():
        if _surface_pattern(surface).search(lowered):
            found.add(canon)
    return found


def technology_terms_in_text(text: str) -> set[str]:
    """Return configured skills plus technology-like terms named in JD skill cues.

    This keeps an unfamiliar named tool visible in the final Technical Skills
    block even before someone adds an alias to ``skill_aliases.yaml``.
    """
    found = canonical_skills_in_text(text)
    for cue in _TECH_CUE.finditer(text):
        phrase = cue.group(1)
        for item in re.split(r",|/|\band\b|\bor\b", phrase, flags=re.I):
            candidate = item.strip(" .()[]")
            words = candidate.split()
            if not candidate or len(words) > 4 or candidate.casefold() in _TECH_STOP:
                continue
            if (candidate.casefold() in _MAP or _TECH_SHAPE.search(candidate)
                    or candidate[:1].isupper()):
                found.add(canonical(candidate))
    return found
