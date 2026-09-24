"""Integration check for raw resume generation from a local Ollama instance.

Usage:
    python scripts/llm_resume_structure_integration.py
    python scripts/llm_resume_structure_integration.py --host http://localhost:11434

The response is deliberately checked before any client-side cleanup so parser
artifacts, Markdown fences, and conversational filler cannot be hidden.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MODEL = "dolphin-llama3"
TEMPERATURE = 0.15
SYSTEM_PROMPT = """Return only resume content. Do not greet the user, explain the
output, use code fences, or include reasoning tags. Preserve each project as a
separate Markdown heading followed by its own bullets."""
PROMPT = """Write a compact resume in Markdown for this candidate.

# Jordan Lee
## Summary
Backend engineer specializing in AI application delivery.
## Selected Projects
### Project 1 - Knowledge Assistant
Technologies: LangChain, FastAPI, Python
- Built a retrieval workflow for internal knowledge search.
### Project 2 - Service Platform
Technologies: FastAPI, PostgreSQL, Docker
- Built an API platform for authenticated customer workflows.

Required output rules:
1. Include the exact, separate headings "Project 1" and "Project 2".
2. Keep LangChain and FastAPI in the resume.
3. Return only the resume Markdown."""


@dataclass(frozen=True)
class Metric:
    name: str
    passed: bool
    detail: str


def _contains_project_heading(raw: str, project: str) -> bool:
    """A project must be a heading, not merely text absorbed into a bullet."""
    pattern = rf"(?im)^\s*(?:#{{1,6}}\s+)?{re.escape(project)}\b"
    return bool(re.search(pattern, raw))


def validate_raw_response(raw: str) -> list[Metric]:
    lowered = raw.casefold()
    filler_patterns = (
        r"\bsure\s*,?\s+here(?:'s|\s+is)\s+(?:your|the)\s+resume\b",
        r"\bhere(?:'s|\s+is)\s+(?:your|the)\s+resume\b",
        r"\b(?:i have|i've) (?:created|prepared|written)\b",
        r"\b(?:of course|certainly)!?\b",
    )
    found_filler = next((pattern for pattern in filler_patterns if re.search(pattern, lowered)), None)
    project_1 = _contains_project_heading(raw, "Project 1")
    project_2 = _contains_project_heading(raw, "Project 2")
    metadata_missing = [word for word in ("LangChain", "FastAPI") if word.casefold() not in lowered]
    artifacts = [token for token in ("<think>", "</think>", "```") if token in lowered]

    return [
        Metric("No Conversational Filler", found_filler is None,
               "no conversational introduction found" if found_filler is None else f"matched {found_filler!r}"),
        Metric("Structural Integrity", project_1 and project_2,
               "separate Project 1 and Project 2 headings found" if project_1 and project_2
               else "missing a separate heading for " + ", ".join(
                   name for name, exists in (("Project 1", project_1), ("Project 2", project_2)) if not exists)),
        Metric("Metadata Retention", not metadata_missing,
               "LangChain and FastAPI retained" if not metadata_missing else "missing " + ", ".join(metadata_missing)),
        Metric("Clean Artifacts", not artifacts,
               "no think tags or Markdown code fences found" if not artifacts else "found " + ", ".join(artifacts)),
    ]


def request_raw_response(host: str, model: str, timeout: float) -> str:
    endpoint = host.rstrip("/") + "/api/chat"
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": PROMPT}],
        "stream": False,
        "think": False,
        "options": {"temperature": TEMPERATURE, "num_ctx": 8192, "seed": 42},
    }
    request = Request(endpoint, data=json.dumps(payload).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise RuntimeError(f"Ollama returned HTTP {exc.code}: {exc.read().decode('utf-8', 'replace')}") from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach Ollama at {endpoint}: {exc.reason}") from exc
    try:
        raw = body["message"]["content"]
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Ollama response: {body!r}") from exc
    if not isinstance(raw, str) or not raw.strip():
        raise RuntimeError("Ollama returned an empty response")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate raw local-Ollama resume output structure.")
    parser.add_argument("--host", default=os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--show-response", action="store_true", help="Print the raw model response after metrics.")
    args = parser.parse_args()
    print(f"Requesting {args.model} at temperature {TEMPERATURE:.2f} from {args.host} ...")
    try:
        raw = request_raw_response(args.host, args.model, args.timeout)
    except RuntimeError as exc:
        print(f"FAIL  Request: {exc}")
        return 2
    metrics = validate_raw_response(raw)
    for metric in metrics:
        print(f"{'PASS' if metric.passed else 'FAIL'}  {metric.name}: {metric.detail}")
    if args.show_response:
        print("\n--- RAW RESPONSE ---\n" + raw)
    return 0 if all(metric.passed for metric in metrics) else 1


if __name__ == "__main__":
    sys.exit(main())
