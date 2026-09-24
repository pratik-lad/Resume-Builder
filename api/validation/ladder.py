"""Runs the validation layers cheapest-first and stops at the first failure.

Ordering matters: L1 and L2 are set operations costing microseconds and catch
most real problems. L3 costs an embedding call. L4 (V2) costs a model call.
Never pay for an expensive check when a free one already rejected the output.
"""
from schemas import Violation
from validation import drift_guard, entity_guard, nli_guard, numeric_guard, verb_ladder


def validate(output: str, evidence: str, allowed: set[str],
             use_nli: bool = False) -> list[Violation]:
    if not output or not output.strip():
        return [Violation(layer="L0", detail="empty output")]

    for layer in (
        lambda: entity_guard.check(output, allowed),   # L1
        lambda: numeric_guard.check(output, evidence), # L2
        lambda: verb_ladder.check(output, evidence),   # L5
        lambda: drift_guard.check(output, evidence),   # L3
    ):
        found = layer()
        if found:
            return found

    if use_nli:
        return nli_guard.check(output, evidence)
    return []


def unsupported_claim_rate(texts: list[str], allowed: set[str]) -> float:
    """UCR = unsupported tokens / total significant tokens. Target: 0.00."""
    total = bad = 0
    for text in texts:
        text_bad, text_total = entity_guard.claim_token_counts(text, allowed)
        bad += text_bad
        total += text_total
    return round(bad / total, 4) if total else 0.0
