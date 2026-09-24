# Phase 2 baseline evaluation

Run date: 2026-09-22 (Asia/Kolkata)

## Gate result

**FAIL - not ready to use this set as the documented 50-pair Phase 2 baseline.**

The file contains 50 rows, but only 46 have accepted human gold annotations. Pairs 43, 44, 49, and 50 are `proposal_rejected`; their four `gold_*` fields are blank. They were excluded rather than inferred or replaced by proposals.

The 46 accepted rows passed structural and provenance validation: all four gold fields are present, statuses are valid, pair IDs are unique, fact and requirement IDs resolve, requirement matches reference valid IDs, facts and requirements are source-supported, and no JD-only entity appears in `gold_entities`.

The accepted subset still covers 20 resumes and 25 JDs. The source datasets and gold CSV were unchanged (SHA-256 checks passed).

## Results

| Metric | Actual | Project target | Result |
| --- | ---: | ---: | --- |
| Complete accepted gold pairs | 46 / 50 | 50 | **FAIL** |
| Requirement-level matching accuracy | 83.97% (791/942) | >= 80% | **PASS**, provisional because only 46 pairs are accepted |
| Requirement-level Cohen's kappa | 0.711 | >= 0.65 | **PASS**, provisional |
| Whole-pair fit accuracy | 63.04% (29/46) | >= 80% | **FAIL** |
| Whole-pair Cohen's kappa | 0.319 | >= 0.65 | **FAIL** |
| Mismatch rejection at unchanged `<25` gate | recall 42.86%, precision 90.00%, F1 58.06% (TP 9, FP 1, FN 12, TN 24) | reliable rejection; no numeric target defined | **FAIL** |
| Requirement type classification | 82.13% on 912 aligned requirements; kappa 0.727; alignment coverage 96.82% | no numeric target defined | **NOT MEASURABLE** against a target |
| Required/preferred (`must_have`) classification | 99.56% on 912 aligned requirements; kappa 0.974 | >= 85% | **PASS** |
| JD extraction exact-phrase F1 | 84.29% (P=84.29%, R=84.29%) | no JD extraction-F1 target defined | **NOT MEASURABLE** against a target |
| Resume fact extraction F1 | unavailable | >= 0.85 on 10 linked resumes | **NOT MEASURABLE** |
| Existing checker UCR on structured-profile rewrites | 5.48% (4/73 significant tokens) | 0.00 | **FAIL** |
| Hallucination attack tests | 17/17 passed | all caught | **PASS** |
| Rewrite latency | p50 3.42 s, p95 5.65 s (33 jobs with rewrites) | Phase 2: 40% improvement vs baseline | **NOT MEASURABLE** until a tuned comparator exists |
| Rewrite first-pass rate | 0.00% (0/59) | Phase 2: +10 percentage points vs baseline | **NOT MEASURABLE** as an improvement; baseline is poor |
| Rewrite revert rate | 91.53% (54/59) | recorded, no fixed threshold | **NOT MEASURABLE** against a target |
| JD extraction latency | p50 31.57 s, p95 79.87 s, max 144.34 s (25 JDs) | recorded, no fixed component target | **NOT MEASURABLE** against a target |
| Match latency | p50 0.104 s, p95 0.276 s (46 pairs) | recorded, no fixed component target | **NOT MEASURABLE** against a target |
| Real-PDF API upload-to-render latency | p50 90.22 s, p95 94.69 s (3 fresh runs) | p50 <= 60 s on RTX 3050 | **FAIL** |
| Blind A/B preference | unavailable | >= 60% prefer tuned | **NOT MEASURABLE** |
| Coverage delta / ATS lint / peak RAM-VRAM | not instrumented in this run | record in baseline | **NOT MEASURABLE** |

The latency run used the provided `PratikBugade__2026.pdf` against the DevOps JD and called the five API stages with fresh uploads. Totals were 95.19 s, 78.11 s, and 90.22 s. Median component times were dominated by resume ingest (about 53.95 s) and JD extraction (27.38 s); rewrite p50 was 3.96 s. All three rendered with API-reported UCR 0. This did not exercise n8n, so it is an API end-to-end timing diagnostic; adding orchestration cannot make the measured API path pass 60 seconds.

## Failed metrics and investigation targets

1. **Only 46 accepted pairs.** Pairs 43, 44, 49, and 50 must receive completed human gold annotations before the documented 50-pair gate can be certified. The evaluator correctly excludes them in `eval/human_gold_baseline.py`.

2. **Whole-pair fit accuracy and kappa.** Seventeen human `partial` pairs were classified as `mismatch`. Investigate score calibration and decision bands in `api/matching/matcher.py`, `api/matching/scorer.py`, and `api/review.py::_decision_from_score`. Do not change the 50/75 bands without fitting them on reviewed labels and evaluating on a held-out set.

3. **Mismatch rejection.** Twelve of 21 human mismatches scored at or above the unchanged production gate of 25. Investigate semantic calibration/evidence selection in `api/matching/matcher.py`, qualification rules in `api/matching/qualifications.py`, and aggregate weighting in `api/matching/scorer.py`. Example: pair 20 scored 47.8 because `8-10 years' post-qualification experience` received full years credit and qualification coverage became 100%. The production gate is defined by `LOW_FIT_SCORE` and duplicated in `n8n/workflows/resume-optimize.json`; it was not changed.

4. **Requirement typing.** Of the aligned gold hard skills, 162 were predicted as qualifications. Production extraction in `api/pipeline/jd.py` consumes the LLM output directly, while atomic/type correction in `api/review_annotations.py::requirement_atoms` is review-only. Investigate `api/prompts/jd_extraction.jinja` and add a deterministic production normalization stage that preserves alternatives and conjunction semantics.

5. **UCR and rewrite reliability.** The token checker reported 5.48%, and only 5 of 59 rewrites were accepted; 54 reverted. There were 162 `L0: empty output` repair events. Investigate `api/llm/structured.py`, `api/pipeline/optimize.py`, and the rewrite/repair prompts. Also reconcile `api/validation/entity_guard.py::check` with `api/validation/ladder.py::unsupported_claim_rate`: accepted text can pass the morphology/generic-word guard but still receive non-zero exact-token UCR. Generic, unsupported claims such as "performs maintenance and support" can pass when rewriting a role-title-only fact, so semantic entailment needs stronger evidence handling.

6. **End-to-end latency.** Ingest is the largest cost because `api/pipeline/ingest.py::build_ledger` makes one LLM call per detected section; JD extraction is the second-largest cost in `api/pipeline/jd.py::extract`. Investigate batching/caching and prompt/schema size while preserving accuracy. The first match run also paid an embedding warm-up cost (8.82 s; later runs were 0.36-0.43 s).

## Test and integrity record

- Full test suite: **61 passed**, 5 third-party SWIG deprecation warnings.
- Hallucination/validation subset: **17 passed**.
- Gold CSV unchanged: yes.
- Source datasets unchanged: yes.
- Proposal annotations used as ground truth: no.
- Fine-tuning performed: no.
- Thresholds changed: no.

Machine-readable results are in `report.json`; real-PDF latency details are in `api-latency.json`.
