"""Build/release gate: compare ONNX against original BGE on repository gold facts.

Run with the existing development Python (which has sentence-transformers).
Neither PyTorch nor this script is used by the shipped desktop app.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from desktop.bootstrap import initialize
    initialize()
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from matching import embedder, matcher
    from schemas import Fact, Requirement, RequirementSet
    reference = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu", local_files_only=True)
    reference.max_seq_length = 512
    reference.encode(["warmup"], normalize_embeddings=True)
    rows = list(csv.DictReader((ROOT / "data/evaluation/gold_label_review.csv").open(encoding="utf-8-sig")))
    examples = []
    for row in rows:
        facts = [Fact(**item) for item in json.loads(row["gold_facts"] or "[]")]
        reqs = [Requirement(**item) for item in json.loads(row["gold_requirements"] or "[]")]
        if facts and reqs:
            examples.append((row["resume_id"], row["jd_id"], facts, reqs))
    if not examples:
        raise RuntimeError("No gold fixtures are available; release gate cannot pass.")
    embedder.available = lambda: True
    embedder.encode = lambda texts: np.asarray(reference.encode(texts, normalize_embeddings=True, show_progress_bar=False), dtype=np.float32)
    before = []
    for _, _, facts, reqs in examples:
        source = "\n".join(f"{fact.context} {fact.text}" for fact in facts)
        before.append(matcher.match(reqs, facts, source, req_set=RequirementSet(requirements=reqs)))
    from desktop.embedding import install
    install()
    same, total, differences = 0, 0, []
    for example, original in zip(examples, before):
        resume_id, jd_id, facts, reqs = example
        source = "\n".join(f"{fact.context} {fact.text}" for fact in facts)
        current = matcher.match(reqs, facts, source, req_set=RequirementSet(requirements=reqs))
        for a, b in zip(original, current):
            total += 1
            same += a.status == b.status
            if a.status != b.status:
                differences.append({"resume_id": resume_id, "jd_id": jd_id, "requirement": a.req_id,
                                    "torch": a.status, "onnx": b.status})
    agreement = same / total
    result = {"fixture_pairs": len(examples), "classifications": total, "agreement": agreement,
              "passed": agreement >= .95, "differences": differences,
              "source": "Reconstructed context/text from repository gold_facts; identical source for both models."}
    (ROOT / "build/desktop-embedding-validation.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit("ONNX agreement is below 95%; installer is not release-ready.")


if __name__ == "__main__":
    main()
