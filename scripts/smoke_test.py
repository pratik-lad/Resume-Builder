"""End-to-end smoke test against a running API.

    python scripts/smoke_test.py resume.pdf jd.txt [http://localhost:8000]
"""
import sys
import time

import httpx


def main() -> int:
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    resume_path, jd_path = sys.argv[1], sys.argv[2]
    base = sys.argv[3] if len(sys.argv) > 3 else "http://localhost:8000"
    jd_text = open(jd_path, encoding="utf-8").read()

    with httpx.Client(base_url=base, timeout=600.0) as c:
        print("health:", c.get("/health").json())

        t0 = time.perf_counter()
        with open(resume_path, "rb") as fh:
            r = c.post("/v1/ingest", files={"file": (resume_path, fh)}).raise_for_status().json()
        run_id = r["run_id"]
        print(f"[1] ingest      {r['fact_count']} facts  sections={r['sections']}")

        c.post("/v1/jd/extract", json={"run_id": run_id, "jd_text": jd_text}).raise_for_status()
        print("[2] jd/extract  ok")

        m = c.post("/v1/match", json={"run_id": run_id}).raise_for_status().json()
        print(f"[3] match       score_before={m['score_before']['jd_alignment_score']}  "
              f"missing={len(m['gap_report']['missing_required'])}")

        o = c.post("/v1/optimize", json={"run_id": run_id}).raise_for_status().json()
        print(f"[4] optimize    accepted={o['accepted']} unchanged={o.get('unchanged', 0)} "
              f"reverted={o['reverted']} UCR={o['ucr']}")

        if o["ucr"] > 0:
            print("!! UCR > 0 -- render would be blocked. This should never happen.")
            return 1

        d = c.post("/v1/render", json={"run_id": run_id}).raise_for_status().json()
        print(f"[5] render      score_after={d['score_after']['jd_alignment_score']}")
        print(f"\ntotal {time.perf_counter() - t0:.1f}s")
        print(f"report:   {base}{d['report_url']}")
        print(f"download: {base}{d['download_url']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
