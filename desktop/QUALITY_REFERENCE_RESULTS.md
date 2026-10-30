# Project Edition 1.6.0 verification

Follow-up field-boundary fix (2026-10-29): source identity/contact extraction now rejects descriptive prose, role-planning fields are type-checked, and summary validation detects copied project titles, role titles and overviews. The existing requirement assignment, project evidence, skills generation and layout pipeline remain in place. A separate frozen installer is `dist/ResumeOptimizerProjectsSetup-1.6.0-field-fix.exe` (SHA-256 `8fbd2c492e5157093ffb82d71a8a45a8a068b311cd8b6d7e14ff82e1cb671c93`). Python syntax compilation and `git diff --check` passed; the behavioral regression suite was not rerun for this follow-up.

Full fictional professional generation remains enabled. The reference layout, complete JD ledger, 11-call base workflow, bounded repairs, CUDA offloading and edited-text exports are implemented. This report records observed results, not an external ATS score.

## Build and model

- Regression suite: **157 passed**, five existing PyMuPDF/SWIG warnings, 151.64 seconds.
- Selected model: **Qwen3-4B-Instruct-2507 Q4_K_M**, 2,497,281,120 bytes; pinned revision and checksum in `desktop/assets.json`.
- Runtime: llama.cpp b11316, source-pinned CUDA build plus CPU fallback. All selected qualification runs offloaded **37/37 layers**.
- Installer: `dist/ResumeOptimizerProjectsSetup.exe`, 3,045,329,767 bytes; SHA256 `62fe3870c1f68df0d314fe8bc915f3904d25192200dbb3e0b6fc2b0d853890b6`.
- Rollback: `dist/ResumeOptimizerProjectsSetup-1.5.0-4B.exe`; older installers and saved data retained.

## Candidate comparison

Same revised pipeline and three fresh full-stack generations per candidate:

| Candidate | Complete runs | Generation seconds | Observation |
|---|---:|---|---|
| Qwen3-4B-Instruct-2507 | 3/3 | 77.940, 82.009, 96.005 | All six summary bullets model-written; selected. |
| Qwen3.5-4B | 3/3 | 119.792, 118.936, 118.600 | Frequent structured summary fallbacks and technical contradictions. |
| Phi-4-mini-instruct | 1/3 | 87.375 successful; failures at 56.392 and 33.438 | Short responsibilities/placeholders; not selected. |

Earlier nine-fixture comparison attempts, including failures caused by an overly strict overview-length validator, remain under `build/quality-benchmark/`. Short usable overviews now produce warnings instead of aborting a resume.

## Frozen-worker cold/warm qualification

Host: Windows 11 x64, Core i5-13450HX (10 physical cores), approximately 16 GB RAM, RTX 3050 Laptop 6 GB, driver 581.86, plugged in. Scope: source Qt GUI controller with the real packaged worker, Generate through editable preview and autosave, no Python or CUDA SDK on worker PATH. This is not a clean 8 GB machine test.

| Fixture/run | Seconds | Actual calls | Peak process-tree GiB | Device-wide GPU MiB | Mandatory supported/partial/missing |
|---|---:|---:|---:|---:|---|
| full-stack-cold | 78.777 | 14 | 2.982 | 4303 | 12/8/2 |
| full-stack-warm | 75.585 | 13 | 2.690 | 4334 | 18/2/2 |
| salesforce-cold | 80.511 | 13 | 2.964 | 4217 | 1/5/1 |
| salesforce-warm | 65.067 | 13 | 2.552 | 4215 | 2/5/0 |
| java-cold | 80.435 | 15 | 2.952 | 4256 | 2/2/1 |
| java-warm | 69.156 | 15 | 2.948 | 4168 | 3/2/0 |
| databricks-cold | 101.686 | 14 | 2.943 | 4069 | 4/16/1 |
| databricks-warm | 91.240 | 14 | 2.929 | 4217 | 3/16/2 |
| aws-cold | 87.723 | 13 | 2.929 | 4234 | 13/8/6 |
| aws-warm | 81.586 | 14 | 2.938 | 4194 | 14/4/9 |
| azure-genai-cold | 78.840 | 13 | 2.918 | 4140 | 1/2/2 |
| azure-genai-warm | 67.227 | 13 | 2.933 | 4144 | 0/2/3 |
| qa-cold | 62.998 | 13 | 2.930 | 4053 | 2/3/0 |
| qa-warm | 53.233 | 14 | 2.931 | 4070 | 2/2/1 |

All 14 runs finished below 300 seconds; selected-run range **53.233?101.686 seconds**. Peak combined process-tree RSS was **2.982 GiB**. GPU figures are device-wide and include other applications; they are not isolated application VRAM. Every run retained the full three-project document. Actual calls were 13?15, including retries/repairs; the base is 11 and the hard ceiling is 27.

All extracted mandatory keyword sets were present in these 14 outputs. This does **not** establish complete implementation evidence: the table deliberately retains partial/missing capabilities. Full-stack warm output supported 18/22 mandatory capabilities, with two partial and two missing; all three preferred capabilities were supported. The capability classifiers overlap and are conservative local checks. Unknown implementations require human review. Full per-capability passages and warnings are in each HTML report.

Some overview/summary lengths remain below the desired range. Java warm uses structured fallback for both summary halves; Databricks uses a fallback for its first half. Technical warnings include ambiguous percentages, missing implementation mechanisms and unexplained cloud/authentication boundaries. Databricks, AWS and Azure evidence remains below the desired complete-coverage target; do not interpret timing success as final quality approval.

A controlled memory probe found full GPU offloading at 3.61 GiB Windows job commit but 2.76 GiB resident RAM. The job commit cap is now 4 GiB, while the independent 4 GiB GUI/worker RSS monitor remains. **No 2.3 GB startup free-memory gate is present.**

## Local acceptance checks

Final frozen-worker DOCX and HTML exports passed for all seven fixtures, including edited-text authority and bundled-asset verification. Active generation cancellation acknowledged in **0.0187 seconds**; all owned processes were gone after 750 ms. A third fresh full-stack GUI run completed in **88.298 seconds**, 13 calls, **2.987 GiB** peak RSS, no recorded errors; manual edit handling took 0.002 seconds and preview/autosave took 0.0252 seconds. The maximum measured event-loop gap was 0.1733 seconds, so the strict 100 ms interaction target is not established by this run. Isolated installer lifecycle checks **passed** against this exact release: initial install 83.406 seconds, upgrade 40.298 seconds, native GUI startup/self-close 2.355 seconds, uninstall 1.054 seconds. All 161 installed assets verified. Saved test data survived; existing application registry and draft hashes remained unchanged. The QA installer used a separate application identity so the existing app could coexist.

- `build/model-candidates/installer-validation16.json`
- `build/quality-benchmark/release-samples/release-export-checks.json`
- `build/model-candidates/final16-active-cancel-check.json`
- `build/quality-benchmark/final-gui-smoke.json`

Visual review: the fresh full-stack DOCX renders as four pages with six summary bullets, blue headings, bold skill categories, three complete project metadata tables, visible employers and certifications. All three Target Role and Confidential client entries survive pagination. The last page is sparse after a responsibility continues from page three; fixed page count is not forced. No calendar dates were found in generated sections.

Per-run request details are in `build/quality-benchmark/release-samples/request-budget-results.json`: 11,407?20,246 input tokens and 2,091?2,716 output tokens across each full run.

## Install and rollback

1. Close Project Edition before upgrading; leave the separate original application alone.
2. Run `dist/ResumeOptimizerProjectsSetup.exe` and open Resume Optimizer Project Edition.
3. Choose a text PDF/DOCX, paste a JD, Generate, review warnings, edit and export DOCX/HTML.
4. To roll back, close Project Edition and install `dist/ResumeOptimizerProjectsSetup-1.5.0-4B.exe`. Saved user data is preserved; keep a backup before any downgrade.

Developer rebuild:

```powershell
.\desktop\build_projects.ps1 -NSISCompiler '.\build\nsisbi\nsisbi-3.12.3\Bin\makensis.exe'
```

## User smoke checklist

- Install and launch; choose a readable PDF/DOCX and paste your next JD.
- Generate and inspect six summary bullets, numeric experience, three distinct employer/project blocks, certifications and date-free content.
- Edit a section, undo/redo, close/reopen and confirm saved edits.
- Save DOCX and HTML; confirm both contain your edits and review the HTML evidence gaps.
- Cancel during generation; confirm the interface remains usable.
- Keep the 1.5.0 installer and a user-data backup for rollback.

## Remaining release gates

- Actual 8 GB reference laptop benchmark and physically disconnected clean Windows installation without Python/developer tools.
- Manual technical review and user approval of generated quality; complete required-capability implementation is not yet demonstrated for every fixture.
- Performance on other GPUs/CPU-only hosts is not represented by the RTX 3050 results. Automatic fallback paths have regression coverage; actual Metal/Mac hosting is Phase 2 and remains deferred.

## Changed files in this working tree

This includes earlier interrupted iterations; no existing user changes were discarded. Build outputs, weights, QA scripts and samples are ignored artifacts, not application source commits.

- `README.md`
- `desktop/PROJECT_EDITION.md`
- `desktop/README.md`
- `desktop/THIRD_PARTY.md`
- `desktop/app.py`
- `desktop/assets.json`
- `desktop/build.ps1`
- `desktop/build_projects.ps1`
- `desktop/desktop.spec`
- `desktop/draft.py`
- `desktop/generation.py`
- `desktop/gui_smoke.py`
- `desktop/installer.nsi`
- `desktop/prepare_assets.py`
- `desktop/project_document.py`
- `desktop/project_generation.py`
- `desktop/project_installer.nsi`
- `desktop/project_rules.py`
- `desktop/quality.py`
- `desktop/runtime.py`
- `desktop/test_desktop.py`
- `desktop/test_project_edition.py`
- `desktop/test_project_quality.py`
- `desktop/windows_job.py`
- `docs/DESKTOP_INSTALLATION.md`
- `docs/DESKTOP_REQUIREMENTS.md`
- `docs/DESKTOP_TECHNICAL_OVERVIEW.md`
- `desktop/FULL_STACK_RESULTS.md`
- `desktop/GENERAL_QUALITY_RESULTS.md`
- `desktop/MAC_HOSTING_PHASE2.md`
- `desktop/MODEL_UPGRADE_RESULTS.md`
- `desktop/PHASE1_RESULTS.md`
- `desktop/QUALITY_REFERENCE_RESULTS.md`
- `desktop/benchmark_quality.py`
- `desktop/build_cuda.py`
- `desktop/certifications.py`
- `desktop/fixtures/full-stack-jd.txt`
- `desktop/fixtures/java-jd.txt`
- `desktop/fixtures/qa-jd.txt`
- `desktop/fixtures/salesforce-jd.txt`
- `desktop/gui_benchmark.py`
- `desktop/installer-toolchain.json`
- `desktop/job_brief.py`
- `desktop/model_candidates.json`
- `desktop/project_experience.py`
- `desktop/project_profile.py`
- `desktop/reference_layout.py`
- `desktop/requirement_ledger.py`
- `desktop/test_general_quality.py`
- `desktop/test_project_profile.py`
- `desktop/test_reference_release.py`
