import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

from dataset_adapter import DatasetAdapter, DatasetPaths, profile_to_fact_ledger  # noqa: E402


def test_external_dataset_adapter_preserves_label_provenance_and_joins(tmp_path):
    resume_path = tmp_path / "resumes.jsonl"
    resume_path.write_text(json.dumps({"personal_info": {}, "experience": [], "education": [], "skills": {}, "projects": [], "certifications": ""}) + "\n", encoding="utf-8")
    jd_dir = tmp_path / "jds"
    jd_dir.mkdir()
    profile = {"profile_id": 1, "roles": ["Backend Engineer"], "skills_primary": ["Python"], "skills_secondary": ["Docker"], "experience_years": 3, "seniority": "Mid", "domains": ["SaaS"], "preferences": {"locations": ["Remote"]}}
    job = {"id": "job_a", "title": "Python Engineer", "description": "Requires Python", "role_family_hint": "backend"}
    files = {
        "scraped_jobs.json": [job],
        "synthetic_profiles.json": [profile],
        "benchmarks.json": {"benchmark_profile": profile, "jobs": [job], "baselines": [{"job_id": "job_a", "skills": 90, "seniority": 80, "domain": 70, "location": 100, "composite": 86, "overqualified": False}]},
        "gold_labels.json": [{"pair_id": "1_job_a", "skills": 88, "seniority": 80, "domain": 70, "location": 100, "composite": 84, "overqualified": False, "reasoning": "reviewed"}],
        "phase2_pairs.json": [], "phase2_labels.json": [], "phase3_pairs.json": [], "phase3_labels.json": [],
    }
    for name, payload in files.items():
        (jd_dir / name).write_text(json.dumps(payload), encoding="utf-8")

    adapter = DatasetAdapter(DatasetPaths(resume_path, jd_dir))
    curated = adapter.curated_cases()
    gold, skipped = adapter.human_gold_cases()
    assert len(curated) == 1 and curated[0].label_source == "curated_baseline"
    assert len(gold) == 1 and gold[0].label_source == "human_reviewed"
    assert skipped == []

    ledger = profile_to_fact_ledger(profile)
    assert any(fact["text"] == "Python" and fact["type"] == "skill" for fact in ledger["facts"])
    assert any(fact["text"] == "3 years of experience" for fact in ledger["facts"])
