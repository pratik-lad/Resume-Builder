"""Text generation through the native llama.cpp GGUF server on the host."""
import logging
import re
import threading
import time
from typing import Any, Optional

import httpx

from config import settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


_stats_lock = threading.Lock()
_call_count = 0


def reset_call_stats() -> None:
    global _call_count
    with _stats_lock:
        _call_count = 0


def call_stats() -> dict[str, int]:
    with _stats_lock:
        return {"llm_calls": _call_count}


def clean_model_text(text: str) -> str:
    """Remove reasoning wrappers and common assistant-role artifacts."""
    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"^\s*(?:assistant\s*:)+\s*", "", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {settings.llm_api_key}"} if settings.llm_api_key else {}


def chat(
    prompt: str,
    model: Optional[str] = None,
    system: Optional[str] = None,
    fmt: Optional[dict[str, Any]] = None,
    temperature: float = 0.0,
    num_ctx: Optional[int] = None,
    num_predict: Optional[int] = None,
) -> str:
    """One non-streaming chat turn, preserving the existing prompt and token limits."""
    if num_ctx is not None and num_ctx > settings.num_ctx:
        raise LLMError(f"Requested context {num_ctx} exceeds server context {settings.num_ctx}.")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    body: dict[str, Any] = {
        "model": model or settings.model_extract,
        "messages": messages,
        "stream": False,
        "temperature": temperature,
        "top_p": settings.top_p,
        "top_k": settings.top_k,
        "min_p": 0.0,
        "presence_penalty": settings.presence_penalty,
        "repeat_penalty": settings.repeat_penalty,
        "seed": settings.seed,
        "stop": [item.strip() for item in settings.stop_sequences.split(",") if item.strip()],
        "reasoning_effort": "none" if not settings.think else "default",
        "chat_template_kwargs": {"enable_thinking": settings.think},
    }
    if num_predict is not None:
        body["max_tokens"] = num_predict
    if fmt is not None:
        body["response_format"] = {"type": "json_schema", "schema": fmt}

    started = time.perf_counter()
    try:
        global _call_count
        with _stats_lock:
            _call_count += 1
        with httpx.Client(timeout=settings.llm_timeout, headers=_headers()) as client:
            response = client.post(f"{settings.llm_host}/v1/chat/completions", json=body)
            response.raise_for_status()
            payload = response.json()
        raw = payload["choices"][0]["message"]["content"]
        if not isinstance(raw, str):
            raise LLMError("The GGUF server returned an empty text response.")
        timings = payload.get("timings") or {}
        log.info("GGUF chat completed in %.1fs; prompt_tokens=%s output_tokens=%s output_tps=%s",
                 time.perf_counter() - started, timings.get("prompt_n"),
                 timings.get("predicted_n"), timings.get("predicted_per_second"))
        return clean_model_text(raw)
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as error:
        raise LLMError(f"GGUF server call failed ({settings.llm_host}): {error}") from error


def health() -> dict[str, Any]:
    try:
        with httpx.Client(timeout=5.0, headers=_headers()) as client:
            ready = client.get(f"{settings.llm_host}/health")
            ready.raise_for_status()
            models = client.get(f"{settings.llm_host}/v1/models")
            models.raise_for_status()
        names = [item["id"] for item in models.json().get("data", [])]
        return {"llm": "up", "backend": "llama.cpp", "models": names}
    except (httpx.HTTPError, KeyError, ValueError) as error:
        return {"llm": "down", "backend": "llama.cpp", "error": str(error), "models": []}
