"""Thin Ollama wrapper. No SDK — just /api/chat over httpx, so the host is explicit."""
import logging
import re
from typing import Any, Optional

import httpx

from config import settings

log = logging.getLogger(__name__)


class OllamaError(RuntimeError):
    pass


def clean_model_text(text: str) -> str:
    """Remove reasoning wrappers and common assistant-role artifacts."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"^\s*(?:assistant\s*:)+\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def chat(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    fmt: Optional[dict[str, Any]] = None,
    temperature: float = 0.0,
    num_ctx: Optional[int] = None,
    num_predict: Optional[int] = None,
) -> str:
    """One non-streaming chat turn. Returns the raw assistant content."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    body: dict[str, Any] = {
        "model": model or settings.model_extract,
        "messages": messages,
        "stream": False,
        # Hybrid-reasoning models (qwen3.x and later) default to emitting a chain-of-
        # thought block before the answer. Measured impact: ~105s -> ~1.4s for a
        # trivial schema call. We never consume the thinking trace, so it's always off.
        "think": settings.think,
        "options": {
            "temperature": temperature,
            "num_ctx": num_ctx or settings.num_ctx,
            "num_predict": num_predict,
            "seed": settings.seed,
            "repeat_penalty": 1.05,
            "top_p": settings.top_p,
            "stop": [item.strip() for item in settings.stop_sequences.split(",") if item.strip()],
        },
    }
    if fmt is not None:
        body["format"] = fmt
    if num_predict is None:
        body["options"].pop("num_predict")

    try:
        with httpx.Client(timeout=settings.llm_timeout) as client:
            r = client.post(f"{settings.ollama_host}/api/chat", json=body)
            r.raise_for_status()
            return clean_model_text(r.json()["message"]["content"])
    except httpx.HTTPError as e:
        raise OllamaError(f"Ollama call failed ({settings.ollama_host}): {e}") from e


def health() -> dict[str, Any]:
    try:
        with httpx.Client(timeout=5.0) as client:
            r = client.get(f"{settings.ollama_host}/api/tags")
            r.raise_for_status()
            names = [m["name"] for m in r.json().get("models", [])]
            return {"ollama": "up", "models": names}
    except httpx.HTTPError as e:
        return {"ollama": "down", "error": str(e), "models": []}
