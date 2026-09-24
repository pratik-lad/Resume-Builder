"""L4 -- NLI entailment. V2, deliberately not implemented in V1.

Catches paraphrase-level inflation that the lexical layers miss
("member of a team" -> "led a team" where the verb ladder has no signal).

Plan: a small cross-encoder NLI model; the cited evidence must ENTAIL the output.
Reject `contradiction` and `neutral`. Costs ~150-400 ms on CPU, so only add it
once eval shows L1/L2/L5 are leaving real errors through.
"""
from schemas import Violation


def check(output: str, evidence: str) -> list[Violation]:
    return []
