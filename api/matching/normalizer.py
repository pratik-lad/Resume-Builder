"""Alias normalisation. 'Postgres', 'postgre sql' and 'PostgreSQL' must become one thing.

This is the boring file that decides how good your matching is.
Grow it from eval failures, not from imagination.
"""
import re
from functools import lru_cache

import yaml

from config import settings

_ALIASES: dict[str, list[str]] = yaml.safe_load(
    (settings.resources / "skill_aliases.yaml").read_text(encoding="utf-8")
)
# alias -> canonical, plus canonical -> itself
_MAP: dict[str, str] = {}
for canon, variants in _ALIASES.items():
    _MAP[canon.lower()] = canon.lower()
    for v in variants or []:
        _MAP[str(v).lower()] = canon.lower()

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
    return out


def canonical_set(terms: list[str]) -> set[str]:
    return {canonical(t) for t in terms if t and t.strip()}


def all_surface_forms(canon_terms: set[str]) -> set[str]:
    out: set[str] = set()
    for c in canon_terms:
        out |= expand(c)
    return out


def canonical_skills_in_text(text: str) -> set[str]:
    """Find configured skills in free text while respecting token boundaries."""
    lowered = text.lower()
    found: set[str] = set()
    for surface, canon in _MAP.items():
        if re.search(rf"(?<![\w+#]){re.escape(surface)}(?![\w+#])", lowered):
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
