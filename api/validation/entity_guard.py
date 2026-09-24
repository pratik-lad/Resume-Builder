"""L1 -- the whitelist. Catches ~80-90% of real hallucinations at zero LLM cost.

ALLOWED = every token in the original resume
        + every surface form of every canonical skill the resume mentions
        + a generic English/resume vocabulary

Anything else appearing in a rewrite is, by construction, not supported by the
resume. This is a set operation, not a judgement call -- which is exactly why
it is trustworthy.
"""
import re
from functools import lru_cache

import yaml
from rapidfuzz import fuzz

from config import settings
from matching import normalizer
from schemas import Violation

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#./\-]*")
_POSSESSIVE_RE = re.compile(r"(?i)([A-Za-z][A-Za-z0-9+#./\-]*)(?:['’]s)\b")
_SUFFIXES = ("ization", "isation", "ations", "ation", "ingly", "ing", "edly",
            "ed", "es", "s", "ly")
_SINGLE_CHARACTER_ENTITIES = {"c"}


@lru_cache(maxsize=1)
def generic_vocab() -> frozenset[str]:
    raw = (settings.resources / "generic_vocab.txt").read_text(encoding="utf-8")
    return frozenset(w.strip().lower() for w in raw.split() if w.strip())


@lru_cache(maxsize=1)
def _ladder_verbs() -> frozenset[str]:
    """Every verb already vetted by the ownership ladder (validation/verb_ladder.py)
    is, by definition, a legitimate action verb -- its RANK is what L5 checks,
    not whether it's allowed to appear at all. Without this union, a word like
    "optimized" could be rejected by L1 for not being in generic_vocab.txt even
    though verb_ladder.yaml already treats it as fully legitimate vocabulary.
    """
    raw = yaml.safe_load((settings.resources / "verb_ladder.yaml").read_text(encoding="utf-8"))
    return frozenset(v.lower() for verbs in raw.values() for v in verbs)


def _stem(word: str) -> str:
    for suf in _SUFFIXES:
        if word.endswith(suf) and len(word) - len(suf) >= 3:
            return word[: -len(suf)]
    return word


@lru_cache(maxsize=1)
def _vocab_stems() -> frozenset[str]:
    return frozenset(_stem(w) for w in generic_vocab() | _ladder_verbs())


def tokens(text: str) -> list[str]:
    # Treat possessives as the underlying word before tokenisation. Otherwise
    # "developer's" / "candidate’s" can leak a meaningless `s` fragment into
    # L1 and waste a repair call. Keep C as a valid one-character language;
    # C++ and C# naturally remain intact in the token regex.
    normalized = _POSSESSIVE_RE.sub(r"\1", text)
    return [token for raw in _TOKEN_RE.findall(normalized)
            if (token := raw.lower().strip(".-/"))
            and (len(token) > 1 or token in _SINGLE_CHARACTER_ENTITIES)]


def build_allowed(resume_text: str, entity_lists: list[list[str]]) -> set[str]:
    allowed = set(tokens(resume_text))
    canon: set[str] = set()
    for group in entity_lists:
        canon |= normalizer.canonical_set(group)
    for surface in normalizer.all_surface_forms(canon):
        allowed |= set(tokens(surface))
    allowed |= canon
    return allowed


def _supported(tok: str, allowed: set[str], allowed_list: list[str]) -> bool:
    vocab = generic_vocab()
    ladder = _ladder_verbs()
    vocab_stems = _vocab_stems()
    if tok in allowed or tok in vocab or tok in ladder:
        return True
    if _stem(tok) in vocab_stems:
        return True
    return bool(allowed_list and max(
        (fuzz.ratio(tok, a) for a in allowed_list if abs(len(a) - len(tok)) <= 3),
        default=0,
    ) / 100.0 >= settings.entity_fuzzy_threshold)


def claim_token_counts(text: str, allowed: set[str]) -> tuple[int, int]:
    """Return unsupported and significant token counts using L1's exact rules."""
    allowed_list = list(allowed)
    significant = [tok for tok in tokens(text)
                   if tok not in generic_vocab() and tok not in _ladder_verbs()]
    return sum(not _supported(tok, allowed, allowed_list) for tok in significant), len(significant)


def check(output: str, allowed: set[str]) -> list[Violation]:
    # Fuzzy morphology tolerance runs against the RESUME's own vocabulary only --
    # never against the generic vocab, which is handled by exact stem matching
    # below. Fuzzing against ~500 generic words would risk accidentally
    # legitimising an invented entity that merely resembles a common word.
    allowed_list = list(allowed)
    violations: list[Violation] = []

    for tok in tokens(output):
        if _supported(tok, allowed, allowed_list):
            continue
        # morphology against generic vocab: "transformed" -> stem "transform" is
        # itself in vocab, or shares a stem with a vocab word ("optimizing" /
        # "optimize"). Exact stem match only -- no fuzz here, see note above.
        violations.append(Violation(
            layer="L1",
            detail=f"'{tok}' does not appear anywhere in the original resume",
        ))
    return violations
