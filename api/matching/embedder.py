"""bge-small-en-v1.5, lazily loaded, in-process, CPU.

Two things people get wrong:
1. Adding the BGE query instruction prefix. That prefix is for ASYMMETRIC retrieval.
   Ours is a symmetric short-phrase-vs-short-phrase task, so the prefix silently
   degrades scores. We do not add it.
2. Standing up an embedding service. 150 short strings takes ~0.4s in-process.
"""
import logging
from typing import Optional

import numpy as np

from config import settings

log = logging.getLogger(__name__)
_model = None
_failed = False


def _load():
    global _model, _failed
    if _model is not None or _failed:
        return _model
    if not settings.embed_enabled:
        _failed = True
        return None
    try:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(settings.embed_model, device="cpu")
        log.info("loaded embedding model %s", settings.embed_model)
    except Exception as e:  # noqa: BLE001 - degrade to lexical-only, never crash a run
        log.warning("embeddings unavailable, falling back to lexical-only: %s", e)
        _failed = True
    return _model


def available() -> bool:
    return _load() is not None


def encode(texts: list[str]) -> Optional[np.ndarray]:
    """Returns L2-normalised vectors, so cosine == dot product."""
    model = _load()
    if model is None or not texts:
        return None
    vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
    return np.asarray(vecs, dtype=np.float32)


def similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """(n_a, n_b) cosine matrix. At our scale this is microseconds -- no vector DB."""
    return a @ b.T
