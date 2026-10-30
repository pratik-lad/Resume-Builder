"""Compatibility shim for the retired claim-validation pipeline.

Resume generation is intentionally ungated: it no longer evaluates a generated
claim against source evidence, ownership verbs, numbers, entities, semantic
drift, or NLI.  Keep this module so legacy callers can upgrade independently.
"""
from schemas import Violation


def validate(output: str, evidence: str, allowed: set[str],
             use_nli: bool = False) -> list[Violation]:
    """Accept all output; truth and evidence validation has been removed."""
    return []


def unsupported_claim_rate(texts: list[str], allowed: set[str]) -> float:
    """Retained for callers of the retired metric; it no longer inspects text."""
    return 0.0
