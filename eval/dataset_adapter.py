"""Read-only adapters for the external resume and job datasets.

The source datasets remain unchanged and outside this repository. This module
maps their existing fields into the Resume Optimizer's evaluation contracts;
it does not promote raw or model-generated records to human gold labels.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable, Iterator


UNKNOWN = {"", "unknown", "n/a", "none", "null"}


def _known(value: Any) -> bool:
    return value is not None and str(value).strip().casefold() not in UNKNOWN


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


@dataclass(frozen=True)
class DatasetPaths:
    resume_jsonl: Path
    jd_dir: Path

    @classmethod
    def from_config(cls, config_path: Path) -> "DatasetPaths":
        data = _load_json(config_path)
        paths = cls(
            resume_jsonl=Path(data["resume_jsonl"]).expanduser(),
            jd_dir=Path(data["jd_dir"]).expanduser(),
        )
        paths.validate()
        return paths

    def validate(self) -> None:
        required = [
            self.resume_jsonl,
            self.jd_dir / "scraped_jobs.json",
            self.jd_dir / "synthetic_profiles.json",
            self.jd_dir / "benchmarks.json",
            self.jd_dir / "gold_labels.json",
            self.jd_dir / "phase2_pairs.json",
            self.jd_dir / "phase2_labels.json",
            self.jd_dir / "phase3_pairs.json",
            self.jd_dir / "phase3_labels.json",
        ]
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise FileNotFoundError("Missing dataset files: " + ", ".join(missing))


@dataclass(frozen=True)
class BenchmarkCase:
    pair_id: str
    profile: dict[str, Any]
    job: dict[str, Any]
    label: dict[str, Any]
    label_source: str


class DatasetAdapter:
    def __init__(self, paths: DatasetPaths):
        self.paths = paths

    def iter_resumes(self) -> Iterator[tuple[int, dict[str, Any]]]:
        with self.paths.resume_jsonl.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if line.strip():
                    yield line_number, json.loads(line)

    def load_jobs(self) -> dict[str, dict[str, Any]]:
        jobs: dict[str, dict[str, Any]] = {}
        for row in self.load_job_records():
            existing = jobs.get(row["id"])
            if existing is not None and existing != row:
                raise ValueError(f"Conflicting duplicate job ID: {row['id']}")
            jobs[row["id"]] = row
        return jobs

    def load_job_records(self) -> list[dict[str, Any]]:
        return _load_json(self.paths.jd_dir / "scraped_jobs.json")

    def load_profiles(self) -> dict[int, dict[str, Any]]:
        return {int(row["profile_id"]): row for row in _load_json(self.paths.jd_dir / "synthetic_profiles.json")}

    def curated_cases(self) -> list[BenchmarkCase]:
        """The 25-case curated regression set, including deliberate mismatches.

        Its labels are useful regression baselines, but the dataset card does
        not identify them as human-reviewed, so they are not called gold.
        """
        payload = _load_json(self.paths.jd_dir / "benchmarks.json")
        profile = payload["benchmark_profile"]
        jobs = {row["id"]: row for row in payload["jobs"]}
        labels = {row["job_id"]: row for row in payload["baselines"]}
        if set(jobs) != set(labels):
            raise ValueError("benchmarks.json jobs and baselines do not have the same IDs")
        return [
            BenchmarkCase(
                pair_id=f"benchmark_profile_{job_id}",
                profile=profile,
                job=jobs[job_id],
                label=labels[job_id],
                label_source="curated_baseline",
            )
            for job_id in jobs
        ]

    def human_gold_cases(self) -> tuple[list[BenchmarkCase], list[str]]:
        """Join the human-reviewed labels to their source profiles and jobs."""
        jobs = self.load_jobs()
        # Two human-reviewed labels reference the curated benchmark jobs rather
        # than scraped_jobs.json. Both files are documented parts of this
        # dataset, so include those jobs without changing either source.
        benchmark_jobs = _load_json(self.paths.jd_dir / "benchmarks.json")["jobs"]
        for job in benchmark_jobs:
            jobs.setdefault(job["id"], job)
        profiles = self.load_profiles()
        cases: list[BenchmarkCase] = []
        skipped: list[str] = []
        for label in _load_json(self.paths.jd_dir / "gold_labels.json"):
            profile_text, separator, job_id = label["pair_id"].partition("_")
            try:
                profile_id = int(profile_text)
            except ValueError:
                skipped.append(label["pair_id"])
                continue
            if not separator or profile_id not in profiles or job_id not in jobs:
                skipped.append(label["pair_id"])
                continue
            cases.append(BenchmarkCase(
                pair_id=label["pair_id"],
                profile=profiles[profile_id],
                job=jobs[job_id],
                label=label,
                label_source="human_reviewed",
            ))
        return cases, skipped

    def inventory(self) -> dict[str, Any]:
        job_records = self.load_job_records()
        jobs = self.load_jobs()
        profiles = self.load_profiles()
        gold, skipped = self.human_gold_cases()
        resume_count = sum(1 for _ in self.iter_resumes())
        phase2_pairs = _load_json(self.paths.jd_dir / "phase2_pairs.json")
        phase2_labels = _load_json(self.paths.jd_dir / "phase2_labels.json")
        phase3_pairs = _load_json(self.paths.jd_dir / "phase3_pairs.json")
        phase3_labels = _load_json(self.paths.jd_dir / "phase3_labels.json")
        return {
            "raw": {
                "resumes": resume_count,
                "job_records": len(job_records),
                "unique_job_ids": len(jobs),
                "identical_duplicate_job_records": len(job_records) - len(jobs),
                "profiles": len(profiles),
            },
            "curated_regression_cases": len(self.curated_cases()),
            "human_gold_labels_total": len(gold) + len(skipped),
            "human_gold_joined": len(gold),
            "human_gold_unjoined_pair_ids": skipped,
            "development_labels": {
                "phase2_pairs": len(phase2_pairs),
                "phase2_labels": len(phase2_labels),
                "phase3_pairs": len(phase3_pairs),
                "phase3_labels": len(phase3_labels),
                "provenance": "model-generated skills labels plus deterministic dimensions",
            },
        }


def profile_to_fact_ledger(profile: dict[str, Any]) -> dict[str, Any]:
    """Map an existing structured profile into current FactLedger JSON.

    Values come only from source fields. The experience sentence is a faithful
    textual representation of the source numeric value so the existing
    qualification rules can evaluate it.
    """
    facts: list[dict[str, Any]] = []
    raw_lines: list[str] = []
    counter = 0

    def add(fact_type: str, text: Any, context: str = "", entities: dict[str, list[str]] | None = None) -> None:
        nonlocal counter
        if not _known(text):
            return
        counter += 1
        value = str(text).strip()
        raw_lines.append(value)
        facts.append({
            "fact_id": f"SRC-{counter:03d}",
            "type": fact_type,
            "parent_id": "structured_profile",
            "context": context,
            "text": value,
            "entities": entities or {"tech": [], "orgs": [], "numbers": [], "dates": []},
            "source": {"page": 1, "char_start": 0, "char_end": 0},
        })

    for role in profile.get("roles", []):
        add("experience_bullet", role, context="roles")
    for skill in profile.get("skills_primary", []):
        add("skill", skill, context="skills_primary", entities={"tech": [skill], "orgs": [], "numbers": [], "dates": []})
    for skill in profile.get("skills_secondary", []):
        add("skill", skill, context="skills_secondary", entities={"tech": [skill], "orgs": [], "numbers": [], "dates": []})
    years = profile.get("experience_years")
    if isinstance(years, (int, float)):
        add("summary", f"{years:g} years of experience", context="experience_years",
            entities={"tech": [], "orgs": [], "numbers": [str(years)], "dates": []})
    add("summary", profile.get("seniority"), context="seniority")
    for domain in profile.get("domains", []):
        add("other", domain, context="domains")

    preferences = profile.get("preferences") or {}
    for location in preferences.get("locations", []):
        if _known(location):
            raw_lines.append(str(location).strip())

    allowed = sorted({
        token.casefold()
        for line in raw_lines
        for token in str(line).replace(",", " ").split()
        if token.strip()
    })
    return {"facts": facts, "allowed_entities": allowed, "raw_text": "\n".join(raw_lines)}


def resume_completeness(record: dict[str, Any]) -> dict[str, Any]:
    """Describe source-field presence without treating the record as gold."""
    personal = record.get("personal_info") or {}
    experience = record.get("experience") or []
    education = record.get("education") or []
    projects = record.get("projects") or []
    skills = record.get("skills") or {}
    technical = skills.get("technical") or {}
    useful_projects = [p for p in projects if _known((p or {}).get("name"))]
    skill_count = sum(
        len([item for item in technical.get(group, []) if _known((item or {}).get("name"))])
        for group in ("programming_languages", "frameworks", "databases", "cloud")
    )
    present = {
        "summary": _known(personal.get("summary")),
        "experience": bool(experience),
        "education": bool(education),
        "skills": skill_count > 0,
        "projects": bool(useful_projects),
        "certifications": _known(record.get("certifications")),
    }
    return {"present": present, "score": sum(present.values()), "skill_count": skill_count}


def stable_record_id(line_number: int, record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"resume-line-{line_number}-{sha256(canonical.encode('utf-8')).hexdigest()[:12]}"
