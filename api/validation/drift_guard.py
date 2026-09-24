"""L3 -- did the rewrite wander off topic entirely?

Cheap safety net for the case where the model answers a different question.
Silently skipped if embeddings are unavailable; L1/L2/L5 still hold the line.
"""
from config import settings
from matching import embedder
from schemas import Violation


def check(output: str, evidence: str) -> list[Violation]:
    if not embedder.available():
        return []
    vecs = embedder.encode([output, evidence])
    if vecs is None or len(vecs) < 2:
        return []
    cos = float(vecs[0] @ vecs[1])
    if cos < settings.drift_threshold:
        return [Violation(
            layer="L3",
            detail=f"rewrite drifted from the evidence (similarity {cos:.2f} < "
                   f"{settings.drift_threshold})",
        )]
    return []
