"""L2 -- invented metrics are the most damaging and most common failure.

"improved performance by 40%" where the resume never mentioned 40 is the single
most credibility-destroying thing this system could produce.
Rule: numbers(output) must be a subset of numbers(evidence).
"""
import re

from schemas import Violation

_NUM_RE = re.compile(r"\d+(?:[.,]\d+)?")


def numbers(text: str) -> set[str]:
    return {m.group(0).replace(",", "") for m in _NUM_RE.finditer(text)}


def check(output: str, evidence: str) -> list[Violation]:
    allowed = numbers(evidence)
    return [
        Violation(layer="L2", detail=f"number '{n}' is not present in the evidence")
        for n in sorted(numbers(output) - allowed)
    ]
