"""Build a compact, review-first Phase 2 evaluation set from external data.

The source data is only read.  The generated CSV intentionally keeps the
project's gold_* fields empty: existing aggregate or model labels are evidence
for a reviewer, not substitutes for fact/requirement/match/entity gold labels.
"""
from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(r"C:/Users/prati/data/resumes/data/jds")
OUTPUT_DIR = ROOT / "data" / "evaluation"


def load(name: str) -> Any:
    with (SOURCE / name).open(encoding="utf-8") as stream:
        return json.load(stream)


def role_family(text: str) -> str:
    text = text.casefold()
    checks = (
        ("backend", ("backend", "node", "java", "python", "api", "software development engineer")),
        ("frontend", ("frontend", "front end", "react", "javascript", "ui engineer")),
        ("fullstack", ("full stack", "fullstack")),
        ("data", ("data engineer", "data scientist", "analytics", "machine learning", "ml engineer")),
        ("devops", ("devops", "platform", "cloud", "sre", "site reliability")),
        ("mobile", ("android", "ios", "mobile")),
        ("product", ("product manager", "product owner", "product engineer")),
        ("finance", ("finance", "accounting", "financial")),
        ("marketing", ("marketing", "growth", "seo")),
        ("sales", ("sales", "business development", "account executive")),
        ("hr", ("recruit", "talent", "human resources", "people partner")),
        ("legal", ("legal", "counsel", "attorney", "compliance")),
        ("operations", ("operations", "supply chain")),
        ("customer_success", ("customer success", "support")),
    )
    for name, terms in checks:
        if any(term in text for term in terms):
            return name
    return "other"


def fit_from_score(score: int | float) -> str:
    if score >= 75:
        return "clear_match"
    if score >= 50:
        return "partial_match"
    return "clear_mismatch"


def proposal_from_pair_type(pair_type: str) -> str:
    return {"positive": "clear_match", "negative": "partial_match", "hard_negative": "clear_mismatch"}[pair_type]


def choose_gold(gold: list[dict[str, Any]], profiles: dict[int, dict[str, Any]], jobs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Choose 15 distinct-profile/JD score labels, balanced high and partial."""
    candidates = []
    for label in gold:
        profile_id_text, _, job_id = label["pair_id"].partition("_")
        profile_id = int(profile_id_text)
        profile, job = profiles.get(profile_id), jobs.get(job_id)
        if not profile or not job:
            continue
        family = role_family(" ".join(profile.get("roles", [])))
        candidates.append((label, profile_id, job_id, family, profile.get("seniority", "Unknown")))
    # Score-label set has no clear mismatches. Take partials first so the final
    # review set does not inherit an all-high-fit bias.
    candidates.sort(key=lambda item: (fit_from_score(item[0]["composite"]) != "partial_match", item[3], item[0]["pair_id"]))
    selected, used_profiles, used_jobs, seen_families = [], set(), set(), set()
    # The source labels cover every seniority. Preserve that coverage rather
    # than allowing an alphabetical role-family sort to select mostly juniors.
    for seniority, quota in (("Junior", 4), ("Mid", 4), ("Senior", 4), ("Staff", 3)):
        for prefer_new_family in (True, False):
            for item in candidates:
                label, profile_id, job_id, family, candidate_seniority = item
                if sum(profiles[row["profile_id"]]["seniority"] == seniority for row in selected) >= quota:
                    break
                if candidate_seniority != seniority or profile_id in used_profiles or job_id in used_jobs:
                    continue
                if prefer_new_family and family in seen_families:
                    continue
                selected.append({"label": label, "profile_id": profile_id, "job_id": job_id, "family": family})
                used_profiles.add(profile_id); used_jobs.add(job_id); seen_families.add(family)
    if len(selected) != 15:
        raise RuntimeError("Could not select 15 distinct human-score-label pairs")
    return selected


def choose_phase3(
    pairs: list[dict[str, Any]], labels: dict[str, dict[str, Any]], profiles: dict[int, dict[str, Any]],
    used_profiles: set[int], used_jobs: set[str],
) -> list[dict[str, Any]]:
    """Choose five new profiles, each with one negative and hard-negative pair."""
    grouped: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for pair in pairs:
        if pair["pair_id"] in labels and pair["profile_id"] not in used_profiles and pair["job_id"] not in used_jobs:
            grouped[pair["profile_id"]].append(pair)
    options = []
    for profile_id, rows in grouped.items():
        negatives = [row for row in rows if row["pair_type"] == "negative"]
        hard = [row for row in rows if row["pair_type"] == "hard_negative"]
        if negatives and hard and profile_id in profiles:
            options.append((profile_id, negatives[0], hard[0]))
    options.sort(key=lambda item: (role_family(" ".join(profiles[item[0]].get("roles", []))), item[0]))
    selected, selected_jobs, seen_families = [], set(), set()
    # Five profiles add one of each seniority plus a second junior so all four
    # experience bands remain represented after the negative examples are added.
    for desired_seniority in ("Junior", "Mid", "Senior", "Staff", "Junior"):
        for profile_id, negative, hard in options:
            family = role_family(" ".join(profiles[profile_id].get("roles", [])))
            if profiles[profile_id].get("seniority") != desired_seniority or family in seen_families:
                continue
            if negative["job_id"] in selected_jobs or hard["job_id"] in selected_jobs:
                continue
            selected.extend((negative, hard))
            selected_jobs.update((negative["job_id"], hard["job_id"]))
            seen_families.add(family)
            break
    if len(selected) == 10:
        return selected
    raise RuntimeError("Could not select ten diverse Phase 3 proposal pairs")


def cross_category(profile: dict[str, Any], job: dict[str, Any]) -> str:
    profile_family = role_family(" ".join(profile.get("roles", [])))
    job_family = job.get("role_family_hint") or role_family(str(job.get("title", "")))
    adjacent = {frozenset(("backend", "fullstack")), frozenset(("frontend", "fullstack")), frozenset(("data", "devops"))}
    if profile_family == job_family:
        return "clear_match"
    if frozenset((profile_family, job_family)) in adjacent:
        return "partial_match"
    return "clear_mismatch"


def source_evidence(label: dict[str, Any] | None) -> tuple[str, str, str, str]:
    if not label:
        return "[]", "[]", "", ""
    matches = json.dumps(label.get("matches", []), ensure_ascii=False)
    gaps = json.dumps(label.get("gaps", []), ensure_ascii=False)
    score = json.dumps({key: label.get(key) for key in ("skills", "seniority", "domain", "location", "composite", "overqualified")}, ensure_ascii=False)
    return matches, gaps, score, str(label.get("label_source", "human_score_label"))


def main() -> None:
    profiles = {int(row["profile_id"]): row for row in load("synthetic_profiles.json")}
    jobs = {row["id"]: row for row in load("scraped_jobs.json")}
    benchmark = load("benchmarks.json")
    jobs.update({row["id"]: row for row in benchmark["jobs"]})
    human_labels = load("gold_labels.json")
    phase3_pairs = load("phase3_pairs.json")
    phase3_labels = {row["pair_id"]: row for row in load("phase3_labels.json")}

    selected_gold = choose_gold(human_labels, profiles, jobs)
    used_profiles = {row["profile_id"] for row in selected_gold}
    used_jobs = {row["job_id"] for row in selected_gold}
    selected_phase3 = choose_phase3(phase3_pairs, phase3_labels, profiles, used_profiles, used_jobs)
    used_profiles.update(row["profile_id"] for row in selected_phase3)
    used_jobs.update(row["job_id"] for row in selected_phase3)
    if len(used_profiles) != 20 or len(used_jobs) != 25:
        raise RuntimeError(f"Expected 20 profiles and 25 jobs, got {len(used_profiles)} profiles and {len(used_jobs)} jobs")

    rows: list[dict[str, str]] = []
    for selected in selected_gold:
        label = selected["label"]
        matches, gaps, score, label_source = source_evidence(label)
        rows.append({
            "resume_id": str(selected["profile_id"]), "jd_id": selected["job_id"],
            "selection_group": "human_score_label", "pair_source": "gold_labels.json (aggregate score only)",
            "proposed_fit_label": fit_from_score(label["composite"]), "proposed_matches": matches,
            "proposed_missing_requirements": gaps, "existing_label_evidence": score,
            "existing_label_provenance": label_source, "gold_facts": "", "gold_requirements": "", "gold_matches": "", "gold_entities": "",
            "review_status": "needs_human_review", "confidence": "medium",
            "review_notes": "Existing human aggregate score can be checked, but project fact/requirement/match/entity gold is still absent.",
        })
    for pair in selected_phase3:
        label = phase3_labels[pair["pair_id"]]
        matches, gaps, score, label_source = source_evidence(label)
        rows.append({
            "resume_id": str(pair["profile_id"]), "jd_id": pair["job_id"],
            "selection_group": "model_label_negative", "pair_source": "phase3_pairs.json + phase3_labels.json",
            "proposed_fit_label": proposal_from_pair_type(pair["pair_type"]), "proposed_matches": matches,
            "proposed_missing_requirements": gaps, "existing_label_evidence": score,
            "existing_label_provenance": label_source, "gold_facts": "", "gold_requirements": "", "gold_matches": "", "gold_entities": "",
            "review_status": "needs_human_review", "confidence": "low",
            "review_notes": "Model-generated/static proposal. Verify the pair type, score, matches, and gaps from source profile and JD.",
        })
    # Add 25 new profile/JD combinations from the same compact source set. They
    # deliberately balance the three fit bands but carry no imported labels.
    existing = {(row["resume_id"], row["jd_id"]) for row in rows}
    buckets: dict[str, list[tuple[int, str]]] = defaultdict(list)
    for profile_id in sorted(used_profiles):
        for job_id in sorted(used_jobs):
            key = (str(profile_id), job_id)
            if key not in existing:
                buckets[cross_category(profiles[profile_id], jobs[job_id])].append((profile_id, job_id))
    wanted = (("clear_match", 8), ("partial_match", 8), ("clear_mismatch", 9))
    selected_cross: list[tuple[str, int, str]] = []
    profile_use = defaultdict(int)
    for row in rows:
        profile_use[int(row["resume_id"])] += 1
    for category, count in wanted:
        if len(buckets[category]) < count:
            raise RuntimeError(f"Not enough {category} cross-pair candidates")
        available = list(buckets[category])
        for _ in range(count):
            # Spread review work across source profiles; each selection updates
            # the count, making this a deterministic round-robin rather than a
            # low-ID-biased slice.
            profile_id, job_id = min(available, key=lambda item: (profile_use[item[0]], item[0], item[1]))
            selected_cross.append((category, profile_id, job_id))
            profile_use[profile_id] += 1
            available.remove((profile_id, job_id))
    for category, profile_id, job_id in selected_cross:
        rows.append({
            "resume_id": str(profile_id), "jd_id": job_id, "selection_group": "deterministic_cross_pair",
            "pair_source": "selected source profile + selected source JD", "proposed_fit_label": category,
            "proposed_matches": "[]", "proposed_missing_requirements": "[]", "existing_label_evidence": "",
            "existing_label_provenance": "deterministic role-family stratification only", "gold_facts": "", "gold_requirements": "", "gold_matches": "", "gold_entities": "",
            "review_status": "needs_human_review", "confidence": "low",
            "review_notes": "No pair label exists. Proposed band is only a role-family stratification; extract and review all project gold fields.",
        })
    if len(rows) != 50:
        raise RuntimeError(f"Expected 50 rows, got {len(rows)}")

    fields = list(rows[0])
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = OUTPUT_DIR / "gold_label_review.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)
    manifest = {
        "purpose": "human-review queue; no row is complete project gold until reviewed",
        "source_datasets_read_only": ["master_resumes.jsonl", "scraped_jobs.json", "gold_labels.json", "phase2_pairs.json", "phase2_labels.json", "phase3_pairs.json", "phase3_labels.json", "benchmarks.json", "synthetic_profiles.json"],
        "raw_resume_note": "Raw master resumes have no stable join to the supplied JD pair labels, so they were not mixed into this matching set.",
        "selected": {"structured_resume_profiles": len(used_profiles), "job_descriptions": len(used_jobs), "pairs": len(rows), "human_score_label_pairs": len(selected_gold), "phase3_model_proposal_pairs": len(selected_phase3), "new_cross_pairs": len(selected_cross)},
        "fit_band_counts": {band: sum(row["proposed_fit_label"] == band for row in rows) for band in ("clear_match", "partial_match", "clear_mismatch")},
        "review_requirement": "All gold_* columns and all proposed labels require human verification. Existing human labels are aggregate score labels, not the README-required project gold schema.",
    }
    (OUTPUT_DIR / "selection_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest["selected"] | {"fit_band_counts": manifest["fit_band_counts"], "csv": str(csv_path)}, indent=2))


if __name__ == "__main__":
    main()
