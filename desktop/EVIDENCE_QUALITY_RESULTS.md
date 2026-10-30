# Project Edition 1.6.1 — resume quality verification

**Subsequent workspace cleanup, 29 October 2026:** the user reported that the app works properly and requested removal of old versions and unwanted artifacts. The current app/installer, source, model, update tools and final verification records remain. Historical rollback installers and superseded benchmark bundles mentioned below were removed. See `docs/WORKSPACE_MAINTENANCE.md` and `build/cleanup-result.json`. The measured limitations below remain unchanged.

Updated 29 October 2026. This is a candidate build: generation, regression and export checks pass, but the strict no-slowdown gate has not passed and technical review items remain. No AI or external API assigns a resume score.

## Implemented changes

- The shared JD brief separates implementation, knowledge, qualifications and recruiter logistics. Salary/timezone lines stay out of career prompts, and onboarding schedule prefixes are removed while their responsibilities remain. Original passages remain available for review.
- Experience parsing handles YOE, ordinary years and separate specialty durations. The higher explicit overall duration is used for fictional generation; conflicting JD totals are reported. The supplied security example now uses 8+ rather than its source's 6+.
- Career planning gives projects different functions, constraints, architecture decisions and ownership. The planned capability focus is passed through to each project writer. Numeric results request a metric, comparable baseline/result, workload, method, window and attributable change; local rules check gaps and arithmetic.
- Technical Skills receives required named terms in consistent categories. Git belongs under version control; cloud products and Experience Cloud remain visible in the main table. Examples such as “or similar” are alternatives. Unknown technologies remain in the brief.
- Six summary bullets follow the completed career. Action-led wording no longer triggers retries demanding generic expertise phrases; local grammar normalization preserves the claims. Existing title, contact and overview leak checks remain.
- Edited section text remains export authority. The HTML review recomputes required terms missing from Technical Skills, implementation passages, experience claims and remaining technical issues.
- The 11-call base workflow, three shared malformed-response retries, two targeted quality repairs and 27-request ceiling remain. A whole-list token-fit check avoids repeated prefix tokenization while preserving the rendered-context limit and oversized-list splitting.

Full fictional professional generation, the reference layout, saved drafts and separate legacy application identity remain in place. The selected model is still Qwen3-4B-Instruct-2507 Q4_K_M with the pinned CUDA/CPU llama.cpp runtimes. No 2.3 GB startup RAM gate was restored.

## Checks completed

- Latest full desktop regression suite: **162 passed**, five existing SWIG warnings, **177.15 seconds** (`build/evidence-fast-full-tests.log`).
- Final focused token-fit, long-ledger, JD hygiene, experience, skills/category merging, arithmetic, edited-report and Education-pagination checks: **7 passed in 19.08 seconds** (`build/evidence-final-format-tests.log`).
- Isolated Qt editing, undo/redo, preview, autosave and reopen checks passed; measured edit handler **0.0024 seconds** (`build/quality-benchmark/evidence-ui-check/results.json`).
- Final frozen-worker exports passed for all nine JDs: **18 original DOCX/HTML exports and 18 edited exports**. Edited text remained authoritative, reduced experience was reported rather than silently corrected, and missing required named skills were checked separately from implementation evidence. All 161 bundled assets passed verification (`build/quality-benchmark/evidence-final-samples/release-export-checks.json`).
- Final owned-worker cancellation acknowledged in **0.0097 seconds**; no recorded owned process remained after 750 ms (`build/model-candidates/evidence-complete-cancel-check.json`).
- The final frozen GUI started and self-closed offline with development-tool paths removed: **3.318 seconds including its two-second self-close delay**, exit 0. This is a smoke check on the development laptop, not a clean-machine installation test.
- Scratch Word renderings of the two final source-generated DOCX samples were reviewed: four pages each, readable headings/tables, Education header kept with its first qualification, and no clipping or overlap (`build/quality-benchmark/evidence-complete-layout-review/results.json`). These are internal review artifacts; no PDF-export feature was added. Word was used for verification, not as an application dependency.

## Final frozen generation measurements

The optimized frozen worker completed all nine fixtures. The real supplied DOCX inputs were used for the first two fixtures. Records are under `build/quality-benchmark/evidence-final3`. Scope is source Qt GUI/controller with the real frozen worker, Generate through editable preview and autosave; exports are separate. Each row is one fresh cold run with a fresh generation identity. The host was plugged in and installer compression was not running during timing.

| JD | Original old-build seconds | Same-session old-build seconds | New frozen seconds | New actual calls |
|---|---:|---:|---:|---:|
| Forward Deployed AI Engineer | 79.744 | 90.071 | 92.908 | 13 |
| Cloud Security / DevSecOps | 78.624 | 80.582 | 86.566 | 13 |
| Full-stack | 74.760 | 65.018 | 88.940 | 14 |
| Salesforce | 72.635 | 85.108 | 81.644 | 13 |
| Java | 69.821 | 72.879 | 76.936 | 13 |
| Databricks | 89.202 | 91.511 | 99.678 | 14 |
| AWS | 80.749 | 76.188 | 83.536 | 13 |
| Azure GenAI | 71.878 | 66.986 | 84.079 | 13 |
| QA | 57.788 | 63.323 | 73.050 | 13 |

All nine completed below 300 seconds. The original old-build median was **74.760 seconds**. Because the usage-limit interruption separated the measurements by several hours, the old build was tested again across all nine fixtures; its same-session median was **76.188 seconds**. The new median is **84.079 seconds**: **10.36% slower** than the same-session control and **12.47% slower** than the original baseline. The five-minute gate passes; the strict no-slowdown gate **fails**. These are single fresh runs with randomized generation; timings vary with output and host load. Both baselines are retained, under `evidence-baseline-valid`, `evidence-current-control` and `evidence-current-control-other`.

Peak combined GUI/worker/model resident memory was **3.002 GiB**; peak device-wide GPU usage was **4,772 MiB**, including other applications. All runs used CUDA with **37/37 layers** offloaded. Maximum sampled Qt event-loop gap was **0.120 seconds**; this does not establish a universal 100 ms interaction guarantee.

The 11-call base and 27-request maximum were preserved; actual submissions include two quality repairs and any malformed-response or transport retries. Eight fixtures used both model-written summary halves; Databricks used a structured fallback for its first half. All had six summary bullets and three complete projects. Final deterministic corrections count literal “Code Quality” separately from implementation evidence, merge equivalent skill-category headings, and keep the Education table header with its first qualification. The generation timing above precedes these local reporting/rendering corrections. They change no model request or generated claim; final samples replay the heading cleanup on untouched generated text, and exports are tested with the corrected frozen worker.

## Remaining quality issues

Required named terms are present in the main Technical Skills section, but this is not complete implementation evidence. Known gaps remain after the two-repair budget. For example, the AI sample still has inconsistent metric naming/context, and the security sample still contains a SAST-versus-image-scanning statement flagged for review. The HTML reports retain the exact passages, missing facets and technical warnings. Do not interpret keyword presence, successful generation or a five-minute timing pass as a 95+ ATS score or final quality acceptance.

The final local implementation checks classify mandatory capabilities as follows. These are conservative, overlapping text checks, not an ATS score or proof that every generated claim is correct. The linked passages and missing facets in each HTML report require manual review.

| JD | Supported | Partial | Missing |
|---|---:|---:|---:|
| Forward Deployed AI Engineer | 4 | 15 | 10 |
| Cloud Security / DevSecOps | 8 | 9 | 12 |
| Full-stack | 11 | 8 | 2 |
| Salesforce | 3 | 4 | 0 |
| Java | 2 | 3 | 0 |
| Databricks | 4 | 15 | 2 |
| AWS | 10 | 7 | 6 |
| Azure GenAI | 0 | 2 | 3 |
| QA | 1 | 4 | 0 |

Frozen DOCX/HTML exports, edited-text checks, cancellation, startup and final layout checks are complete. The candidate is not a declaration that the strict latency requirement or the user's manual resume-quality acceptance has passed. Clean-machine installation, upgrade and uninstall have not been revalidated on a separate Windows machine in this run.

Earlier superseded candidates and their observed regressions remain under `evidence-new-qwen3`, `evidence-revised-qwen3`, `evidence-profile-fixed-qwen3`, `evidence-final` and `evidence-final2`; their partial results are not final acceptance results.

## Files changed for this update

Generation and review: `desktop/generation.py`, `desktop/project_generation.py`, `desktop/project_profile.py`, `desktop/project_experience.py`, `desktop/job_brief.py`, `desktop/project_rules.py`, `desktop/requirement_ledger.py`, `desktop/reference_layout.py`, and new `desktop/evidence_quality.py`.

Verification and packaging: new `desktop/test_evidence_quality.py`; updated `desktop/test_general_quality.py`, `desktop/test_reference_release.py`, `desktop/benchmark_quality.py`, `desktop/gui_benchmark.py`, `desktop/build_projects.ps1`, `desktop/project_installer.nsi`; new `desktop/fixtures/forward-ai-jd.txt` and `desktop/fixtures/cloud-security-jd.txt`.

Documentation: `desktop/PROJECT_EDITION.md`, `desktop/README.md`, `docs/DESKTOP_INSTALLATION.md`, and this report. Existing unrelated working-tree changes have been preserved.

## Candidate installation, samples and rollback

The packaged candidate is `dist/ResumeOptimizerProjectsSetup.exe` (Project Edition 1.6.1), built from `dist/projects-evidence-complete/ResumeOptimizerProjects`. Its checksum and exact size are published in `dist/ResumeOptimizerProjectsSetup.exe.sha256` and `dist/ResumeOptimizerProjects-manifest.json`. This is an unsigned local installer.

Final packaging completed successfully: **3,045,411,566 bytes**, SHA-256 `3d605bd63e5014d2d3255546d28c34e9abec7a10073be767347cf4331abc6978`. A separate hash/size verification matched the final manifest and `git diff --check` passed. The bundled report points to the checksum sidecar; this post-packaging report additionally records the final hash and capability counts.

1. Close Project Edition before running the installer. Use the same install location to update it; the separate legacy application identity and saved user data are preserved.
2. Run the installer, then open **Resume Optimizer Project Edition**. Generate a fresh resume to use the new pipeline; saved drafts are not rewritten automatically.
3. Review Technical Skills and the project evidence in the HTML report. Model warnings and missing implementation evidence remain review items even when required terms are present.

Final sample DOCX and HTML files are under `build/quality-benchmark/evidence-final-samples/`, including `forward-ai.docx`, `forward-ai.html`, `cloud-security.docx` and `cloud-security.html`. Files with `-edited` in the name are deliberate edit-authority tests, not recommended sample resumes.

For rollback, close Project Edition and run the retained `dist/ResumeOptimizerProjectsSetup-1.6.0-field-fix.exe` over the same installation. Back up `%LOCALAPPDATA%/ResumeOptimizerProjectEdition` (or a configured `RESUME_DESKTOP_DATA` location) first. The uninstaller preserves saved user data. The prior latest installer is also retained as a uniquely named `ResumeOptimizerProjectsSetup-backup-*.exe`.

## Limits

Keyword presence does not establish implementation or an external ATS result. Knowledge, qualifications and logistics require separate review. Generated project measurements are fictional, not measured candidate achievements. Remaining model quality issues must stay visible after bounded repairs.

The host is the existing Windows 11 x64 laptop with i5-13450HX, approximately 16 GB RAM and RTX 3050 Laptop 6 GB, plugged in. A clean 8 GB reference-machine benchmark remains unverified.
