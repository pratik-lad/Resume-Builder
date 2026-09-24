"""Run matching baselines against external datasets through the live API.

This harness evaluates matching in isolation by mapping an existing structured
profile to FactLedger JSON and asking the normal API to extract JD requirements
and score the pair. It does not claim extraction F1 or full-pipeline latency.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
from statistics import mean, median
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from hashlib import sha256

from dataset_adapter import BenchmarkCase, DatasetAdapter, DatasetPaths, profile_to_fact_ledger


ROOT = Path(__file__).resolve().parents[1]


def _post(base: str, route: str, payload: dict[str, Any], timeout: int = 300) -> dict[str, Any]:
    request = Request(
        base.rstrip("/") + route,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.load(response)
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{route} returned HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise RuntimeError(f"Cannot reach {base}: {exc.reason}") from exc


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _pearson(left: list[float], right: list[float]) -> float:
    if len(left) < 2 or len(left) != len(right):
        return 0.0
    left_mean, right_mean = mean(left), mean(right)
    numerator = sum((x - left_mean) * (y - right_mean) for x, y in zip(left, right))
    denominator = math.sqrt(
        sum((x - left_mean) ** 2 for x in left) * sum((y - right_mean) ** 2 for y in right)
    )
    return numerator / denominator if denominator else 0.0


def _band(score: float) -> str:
    if score < 50:
        return "low"
    if score < 75:
        return "mid"
    return "high"


def _cohen_kappa(expected: list[str], predicted: list[str]) -> float:
    if not expected or len(expected) != len(predicted):
        return 0.0
    labels = ("low", "mid", "high")
    observed = sum(a == b for a, b in zip(expected, predicted)) / len(expected)
    expected_agreement = sum(
        (expected.count(label) / len(expected)) * (predicted.count(label) / len(predicted))
        for label in labels
    )
    return (observed - expected_agreement) / (1 - expected_agreement) if expected_agreement < 1 else 0.0


def _job_text(job: dict[str, Any]) -> str:
    title = str(job.get("title") or "").strip()
    description = str(job.get("description") or "").strip()
    return "\n\n".join(part for part in (title, description) if part)


def _run_id(case: BenchmarkCase) -> str:
    material = json.dumps({
        "pair_id": case.pair_id,
        "profile": case.profile,
        "job_text": _job_text(case.job),
    }, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "eval-" + sha256(material.encode("utf-8")).hexdigest()[:16]


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    expected_skill = [float(row["expected"]["skills"]) for row in rows]
    predicted_skill = [float(row["predicted"]["hard_skill_coverage"]) for row in rows]
    expected_composite = [float(row["expected"]["composite"]) for row in rows]
    predicted_composite = [float(row["predicted"]["jd_alignment_score"]) for row in rows]
    expected_bands = [_band(value) for value in expected_skill]
    predicted_bands = [_band(value) for value in predicted_skill]
    mismatches = [row for row in rows if float(row["expected"]["skills"]) < 50]
    rejected = [row for row in mismatches if float(row["predicted"]["jd_alignment_score"]) < 25]
    latencies = [float(row["latency_seconds"]) for row in rows]
    return {
        "scope": "matching-only; source structured profiles; live JD extraction; no resume parsing or rewriting",
        "case_count": len(rows),
        "skills_mae": round(mean(abs(a - b) for a, b in zip(expected_skill, predicted_skill)), 3),
        "skills_pearson": round(_pearson(expected_skill, predicted_skill), 3),
        "skill_band_accuracy": round(sum(a == b for a, b in zip(expected_bands, predicted_bands)) / len(rows), 3),
        "skill_band_cohen_kappa": round(_cohen_kappa(expected_bands, predicted_bands), 3),
        "composite_mae_diagnostic": round(mean(abs(a - b) for a, b in zip(expected_composite, predicted_composite)), 3),
        "mismatch_rejection": {
            "expected_mismatches": len(mismatches),
            "rejected_below_project_low_fit_score": len(rejected),
            "recall": round(len(rejected) / len(mismatches), 3) if mismatches else None,
        },
        "latency_seconds": {
            "median": round(median(latencies), 3),
            "p50": round(_percentile(latencies, 0.50), 3),
            "p95": round(_percentile(latencies, 0.95), 3),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "eval" / "datasets.local.json")
    parser.add_argument("--suite", choices=("curated", "human-gold"), default="curated")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--api-base", default="http://localhost:8000")
    parser.add_argument("--runs-dir", type=Path, default=ROOT / "data" / "runs")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    adapter = DatasetAdapter(DatasetPaths.from_config(args.config))
    inventory = adapter.inventory()
    if args.validate_only:
        print(json.dumps(inventory, indent=2))
        return 0

    skipped: list[str] = []
    if args.suite == "curated":
        cases = adapter.curated_cases()
    else:
        cases, skipped = adapter.human_gold_cases()
    if args.limit > 0:
        cases = cases[:args.limit]
    if not cases:
        raise RuntimeError("No benchmark cases are available")

    rows: list[dict[str, Any]] = []
    for position, case in enumerate(cases, start=1):
        run_id = _run_id(case)
        run_dir = args.runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        facts_path = run_dir / "facts.json"
        facts_path.write_text(
            json.dumps(profile_to_fact_ledger(case.profile), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        requirements_cached = (run_dir / "requirements.json").exists()
        started = time.perf_counter()
        requirements = _post(args.api_base, "/v1/jd/extract", {"run_id": run_id, "jd_text": _job_text(case.job)})
        match = _post(args.api_base, "/v1/match", {"run_id": run_id})
        elapsed = time.perf_counter() - started
        row = {
            "pair_id": case.pair_id,
            "job_id": case.job.get("id"),
            "label_source": case.label_source,
            "expected": {key: case.label.get(key) for key in ("skills", "seniority", "domain", "location", "composite", "overqualified")},
            "predicted": match["score_before"],
            "role_title": requirements.get("role_title", ""),
            "requirement_count": len(requirements.get("requirements", [])),
            "requirements_cached": requirements_cached,
            "latency_seconds": round(elapsed, 3),
        }
        rows.append(row)
        print(
            f"[{position}/{len(cases)}] {case.pair_id}: "
            f"expected skills={row['expected']['skills']} predicted hard={row['predicted']['hard_skill_coverage']} "
            f"overall={row['predicted']['jd_alignment_score']} {elapsed:.2f}s"
        )

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "suite": args.suite,
        "inventory": inventory,
        "skipped_pair_ids": skipped,
        "metrics": _metrics(rows),
        "cases": rows,
    }
    output = args.output or ROOT / "eval" / "results" / f"latest-{args.suite}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(result["metrics"], indent=2))
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
