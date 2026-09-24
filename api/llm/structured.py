"""Schema-constrained generation and JSON parsing for extraction."""
import json
import logging
import time
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from llm.client import chat

log = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[-1]
        t = t.rsplit("```", 1)[0]
    # some models wrap JSON in prose; grab the outermost object
    start, end = t.find("{"), t.rfind("}")
    if start != -1 and end > start:
        t = t[start : end + 1]
    return t.strip()


def generate(
    prompt: str,
    schema: Type[T],
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.0,
    retries: int = 1,
) -> T:
    """Generate and parse into `schema`. One retry on a parse failure."""
    last_err: Exception | None = None
    for attempt in range(retries + 1):
        raw = chat(
            prompt=prompt,
            model=model,
            system=system,
            fmt=schema.model_json_schema(),
            temperature=temperature,
        )
        try:
            return schema.model_validate_json(_strip_fences(raw))
        except (ValidationError, json.JSONDecodeError) as e:
            last_err = e
            log.warning("structured parse failed (attempt %s): %s", attempt + 1, e)
            prompt = f"{prompt}\n\nYour previous reply was not valid. Return ONLY valid JSON matching the schema."
    log.error("structured generation gave up: %s", last_err)
    return schema()  # empty instance -- caller decides what to do with nothing


def generate_with_trace(
    prompt: str,
    schema: Type[T],
    model: Optional[str] = None,
    system: Optional[str] = None,
    temperature: float = 0.0,
    retries: int = 1,
) -> tuple[T, list[dict]]:
    """`generate()` semantics plus per-Ollama-call diagnostics.

    This deliberately duplicates the existing parse/retry control flow rather
    than changing it.  The trace is observational: no prompt, retry count,
    validation decision, or returned model value is altered.
    """
    last_err: Exception | None = None
    trace: list[dict] = []
    for attempt in range(retries + 1):
        started = time.perf_counter()
        raw = chat(
            prompt=prompt,
            model=model,
            system=system,
            fmt=schema.model_json_schema(),
            temperature=temperature,
        )
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        record = {
            "ollama_call": attempt + 1,
            "latency_ms": latency_ms,
            "raw_model_output": raw,
            "parsed_output": None,
            "parse_error": None,
        }
        try:
            parsed = schema.model_validate_json(_strip_fences(raw))
            record["parsed_output"] = parsed.model_dump()
            trace.append(record)
            return parsed, trace
        except (ValidationError, json.JSONDecodeError) as exc:
            last_err = exc
            record["parse_error"] = str(exc)
            trace.append(record)
            log.warning("structured parse failed (attempt %s): %s", attempt + 1, exc)
            prompt = f"{prompt}\n\nYour previous reply was not valid. Return ONLY valid JSON matching the schema."
    log.error("structured generation gave up: %s", last_err)
    return schema(), trace
