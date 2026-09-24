"""Run pending sample evaluation cases through the active local API.

Usage:
    python scripts/run_sample_evaluation.py
    python scripts/run_sample_evaluation.py --case SAMPLE-01 SAMPLE-02

The script checkpoints the JSONL manifest after every case. It records run IDs,
latencies, and mechanical output checks, but deliberately never sets the human
review approval fields.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

import httpx
from docx import Document


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "eval" / "sample_cases.pending_review.jsonl"
JD_DOC = ROOT.parents[1] / "Sample JD" / "Sample_Job_Descriptions_Extended.docx"
API = "http://localhost:8000"


def load_jds() -> dict[str, str]:
    document = Document(JD_DOC)
    text = "\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip())
    matches = list(re.finditer(r"(?m)^JD\s+(\d+)\s*:", text))
    if len(matches) < 17:
        raise RuntimeError(f"expected 17 JD sections in {JD_DOC}, found {len(matches)}")
    return {
        match.group(1): text[match.start():matches[index + 1].start() if index + 1 < len(matches) else len(text)].strip()
        for index, match in enumerate(matches)
    }


def load_cases() -> list[dict]:
    return [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]


def save_cases(cases: list[dict]) -> None:
    MANIFEST.write_text("\n".join(json.dumps(case, ensure_ascii=False) for case in cases) + "\n", encoding="utf-8")


def source_path(case: dict) -> Path:
    path = (MANIFEST.parent / case["resume_source"]).resolve()
    # Sample files live beside ``resume-optimizer-poc`` in this local POC;
    # keep manifests portable while supporting that documented sample location.
    if not path.exists():
        path = ROOT.parents[1] / "Sample resumes" / Path(case["resume_source"]).name
    if not path.exists():
        raise FileNotFoundError(path)
    return path


def evaluate_case(client: httpx.Client, case: dict, jds: dict[str, str]) -> None:
    case.pop("run_error", None)
    jd_number = re.search(r"#JD\s+(\d+)$", case["jd_source"])
    if not jd_number:
        raise ValueError(f"invalid jd_source: {case['jd_source']}")
    jd_text = jds[jd_number.group(1)]
    resume = source_path(case)
    timings: dict[str, float] = {}

    started = time.perf_counter()
    with resume.open("rb") as stream:
        response = client.post("/v1/ingest", files={"file": (resume.name, stream, "application/octet-stream")})
    response.raise_for_status()
    ingest = response.json()
    timings["ingest"] = round(time.perf_counter() - started, 2)
    run_id = ingest["run_id"]

    started = time.perf_counter()
    response = client.post("/v1/jd/extract", json={"run_id": run_id, "jd_text": jd_text})
    response.raise_for_status()
    requirements = response.json()
    timings["jd_extract"] = round(time.perf_counter() - started, 2)

    started = time.perf_counter()
    response = client.post("/v1/optimize", json={"run_id": run_id})
    response.raise_for_status()
    optimized = response.json()
    timings["optimize"] = round(time.perf_counter() - started, 2)

    started = time.perf_counter()
    response = client.post("/v1/render", json={"run_id": run_id})
    response.raise_for_status()
    rendered = response.json()
    timings["render"] = round(time.perf_counter() - started, 2)

    markdown = optimized.get("markdown", "")
    expected = case["expected"]
    lowered = markdown.casefold()
    artifacts = ("<think>", "</think>", "missing sections", "new project misplaced", "the new project is missing")
    case["run_id"] = run_id
    case["requirement_count"] = len(requirements.get("requirements", []))
    case["download_url"] = rendered.get("download_url", "")
    case["report_url"] = rendered.get("report_url", "")
    case["latency_seconds"] = timings
    case["automated_checks"] = {
        "expected_employers_present": all(name.casefold() in lowered for name in expected["source_employers"]),
        "expected_projects_present": all(name.casefold() in lowered for name in expected["must_keep_projects"]),
        "expected_technologies_present": all(name.casefold() in lowered for name in expected["must_surface_technologies"]),
        "no_known_model_artifacts": not any(marker in lowered for marker in artifacts),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", nargs="*", help="case IDs to run; defaults to every pending case")
    args = parser.parse_args()
    cases, jds = load_cases(), load_jds()
    wanted = set(args.case or [case["case_id"] for case in cases if not case.get("run_id")])
    with httpx.Client(base_url=API, timeout=360.0) as client:
        for case in cases:
            if case["case_id"] not in wanted:
                continue
            print(f"START {case['case_id']} - {case['jd_title']}", flush=True)
            try:
                evaluate_case(client, case, jds)
                print(f"DONE {case['case_id']} run={case['run_id']} latency={case['latency_seconds']}", flush=True)
            except Exception as exc:
                case["run_error"] = str(exc)
                print(f"FAILED {case['case_id']}: {exc}", flush=True)
            save_cases(cases)


if __name__ == "__main__":
    main()
