"""L5 -- seniority inflation.

The model rarely adds "Kubernetes". It very often turns "contributed to" into
"spearheaded". Lexically that passes every check: the words are ordinary English.
Rule: rank(output verb) <= rank(source verb).
"""
from functools import lru_cache

import yaml

from config import settings
from schemas import Violation


@lru_cache(maxsize=1)
def _ladder() -> dict[str, int]:
    raw = yaml.safe_load((settings.resources / "verb_ladder.yaml").read_text(encoding="utf-8"))
    return {v.lower(): int(rank) for rank, verbs in raw.items() for v in verbs}


def _ranks(text: str) -> list[int]:
    ladder = _ladder()
    return [ladder[w] for w in text.lower().replace(",", " ").split() if w in ladder]


def check(output: str, evidence: str) -> list[Violation]:
    src = _ranks(evidence)
    out = _ranks(output)
    if not out:
        return []
    # no ladder verb in the source -> cap the rewrite at rank 2 ("built"-level)
    ceiling = max(src) if src else 2
    top = max(out)
    if top <= ceiling:
        return []
    ladder = _ladder()
    offenders = [w for w in output.lower().split() if ladder.get(w, 0) > ceiling]
    return [Violation(
        layer="L5",
        detail=(f"ownership upgraded: '{offenders[0] if offenders else 'verb'}' claims more "
                f"than the evidence supports"),
    )]
