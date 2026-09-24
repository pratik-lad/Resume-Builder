"""Create small manifests that reference, but never copy, external datasets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from dataset_adapter import DatasetAdapter, DatasetPaths, resume_completeness, stable_record_id


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=ROOT / "eval" / "datasets.local.json")
    parser.add_argument("--resume-candidates", type=int, default=20)
    args = parser.parse_args()

    adapter = DatasetAdapter(DatasetPaths.from_config(args.config))
    inventory = adapter.inventory()

    candidates = []
    for line_number, record in adapter.iter_resumes():
        quality = resume_completeness(record)
        if quality["score"] < 5:
            continue
        candidates.append({
            "record_id": stable_record_id(line_number, record),
            "source_line": line_number,
            "source_kind": "raw_structured_resume",
            "review_status": "unreviewed_candidate",
            **quality,
        })
    # Hash-based IDs make this deterministic without privileging the first rows.
    candidates.sort(key=lambda row: row["record_id"])
    candidates = candidates[:args.resume_candidates]

    benchmark_dir = ROOT / "eval" / "benchmark"
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    (benchmark_dir / "dataset_inventory.json").write_text(
        json.dumps(inventory, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (benchmark_dir / "resume_candidates.json").write_text(
        json.dumps({
            "status": "candidate_records_only_not_gold",
            "source": adapter.paths.resume_jsonl.name,
            "count": len(candidates),
            "records": candidates,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"inventory": inventory, "resume_candidates": len(candidates)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
