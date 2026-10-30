# Project Edition 1.4.0 ? general quality verification

Updated 26 October 2026. Phase 1 is implemented locally; Phase 2 requires output-quality approval.

## What changed

- A shared versioned JD brief carries role, separate overall/specialty experience, mandatory/preferred requirements, unfamiliar capabilities and certification requirements.
- Planning assigns requirement IDs by business scope. Duplicate model IDs receive one primary owner locally; fixed role stacks and round-robin allocation are removed.
- Summaries request six full sentences after project repair. Bounded failures use a local project-grounded fallback; action phrases, outcome clauses and product capitalization are normalized. Unrecognised non-JD tool labels are excluded from fallback expertise lists.
- Skills retain bold JD-specific headings. The planned stack is authoritative for project metadata, preventing auxiliary tools from replacing core technologies.
- Certifications use an offline ranked catalogue of recognised titles, aliases, status and source references: normally three, two to four when relevant titles are available, required first. Catalogue gaps are reported.
- Full fictional experience, projects, credentials and project metrics remain enabled. New output is date-free, preserves detected identity/education, and contains three visible employers under Relevant Project Experience with Confidential client labels.
- The 2.3 GB startup gate stays removed. The running 4 GiB safeguard, simple interface, owned model processes, saved drafts and legacy edition are preserved.

## Tests and build

- Final source regression suite: **133 passed**, five existing PyMuPDF/SWIG warnings; final packaging log records 138.61 seconds. All seven Salesforce, full-stack, Java, Databricks, AWS, Azure GenAI and QA fixtures are exercised with a stub runtime.
- Real llama.cpp tokenizer preflight: all seven fixture request shapes fit 4,096 tokens with 768 tokens reserved for output; the largest tested stub-generated prompt was 1,556 tokens. Real-model runs also completed their request-size checks.
- Build helper now accepts ordinary native stderr diagnostics and still rejects nonzero native exit codes; exit 7 rejection was checked explicitly.
- Final bundled summary formatter was extracted from the worker PYZ and executed against the measured real-model outputs. Both replay samples pass six-bullet counts, intended word ranges, no summary percentages, cleaned coordinated past-tense phrases, and excluded non-JD unknown summary tool labels.
- The full measured model runs below precede the last deterministic formatter sanitation. The final compiled formatter was replayed without AI calls and final packaged exports were rebuilt from those results. These are not claimed as two fresh end-to-end generations of the final installer.

## Real-model measurements

Host: Windows 11 x64, approximately 16 GB RAM, Intel i5-13450HX / 10 physical cores, four inference threads, CPU inference, Qwen3.5-2B Q4_K_M. Not an 8 GB reference laptop. Other desktop applications remained present; installer compression overlapped part of generation. Logical model submissions exclude bounded transport retries.

| Fixture | Measured full model workflow | Submissions | Peak sampled GUI/worker/model RSS | Final compiled formatter replay |
| --- | ---: | ---: | ---: | ---: |
| Salesforce | 417.741 s | 25 | 2,361,430,016 bytes / 2.20 GiB | 5.704 ms, zero AI calls |
| Java | 353.976 s | 25 | 2,388,328,448 bytes / 2.22 GiB | 4.075 ms, zero AI calls |

Both runs used two project quality calls and at most three shared validation retries, within the 27-submission guard. The Salesforce run recovered one output-token-limit response through its bounded retry. Both summaries used the structured fallback.

Editor handler times were 1.7?1.8 ms and preview/autosave about 15.8?15.9 ms. Maximum measured event-loop gaps were 101.9 ms and 121.6 ms; this does **not** establish that every interaction stays below 100 ms.

## Output checks and remaining gaps

Final worker exports preserve current edited text in DOCX and HTML. A deliberate 4+ years edit remains in both outputs and the report changes to below requirement. Three employer blocks, target roles, client labels, bold categories, date-free education, six bullets per project and certification sections were checked. Autosave recovery, undo/redo and versioned metadata preservation passed in an isolated profile.

| Fixture | Mandatory keyword presence | Mandatory project evidence | Preferred technical keywords/evidence | Certifications |
| --- | --- | --- | --- | --- |
| Salesforce | 7/7 | 1 supported, 6 partial, 0 missing | No preferred technical capability specified; credentials reviewed separately | 4 |
| Java | 9/9 | 4 supported, 0 partial, 1 missing | 2/2 keywords; 1 supported | 3 |

These are literal local heuristics, not an external ATS score. Salesforce still has partial implementation coverage; Java still lacks the requested testing evidence. Literal facet matching can overstate gaps for aliases such as LWC / Lightning Web Components and for unmapped wording. Unknown tools or combinations still require human review. For example, the model introduced JAXA in Java project metadata; it is excluded from the final fallback expertise list but remains a project-review issue.

Project claims also retain metric/workload/baseline/result warnings after the bounded repair budget. The app does not declare these fictional outcomes measured or verified. No 95% external ATS result is claimed.

## Final packaged lifecycle checks

- Active cancellation acknowledged in 13.6 ms; all four owned worker/model processes were gone at the 750 ms check.
- Native GUI created its window and self-closed with Python removed from PATH. The final release is checked again after packaging; see `build/general-quality/frozen-startup.json`.
- Final workers verified offline asset hashes. Missing/corrupt assets, context overflow, low-free-memory startup behavior, queueing, editing, HTML escaping and edition isolation are also regression-tested.
- DOCX and HTML samples: `build/general-quality/Salesforce_sample.docx`, `Salesforce_sample.html`, `Java_sample.docx`, `Java_sample.html`. These are local generated artifacts, not tracked candidate data.

## Installer and rollback

- Version: 1.4.0; installer: `dist/ResumeOptimizerProjectsSetup.exe` (1,402,959,136 bytes).
- SHA-256: `6a10b8dfedc44d69f55fe5da86c95d9bc7c9ddd42b52ec9c5d30448e0ff431c9`.
- Preserved 1.3.0 rollback: `dist/ResumeOptimizerProjectsSetup-backup-9e92e8435568400d98b9f34bc75c755b.exe`.
- Rollback SHA-256: `4c8b5c41d55d1fd05dbf63f4d91eeec39fca88f0f10cbef38f8f74719f3685bc`.
- Close Project Edition and run the latest setup to upgrade. Saved user data is preserved. The original Desktop edition remains separate. No source changes were committed or pushed in this task.

## Release gates

A physically disconnected clean Windows installation, upgrade/uninstall on a clean machine, and an actual 8 GB reference-laptop benchmark remain pending. Removing Python from PATH is not a clean-machine installation test. Mac hosting, Metal inference, remote browser access and tunnel startup are Phase 2 work and are not claimed in this release.

## Files changed in this phase

- `desktop/job_brief.py`, `desktop/certifications.py`: shared requirements, scope assignment and credential catalogue.
- `desktop/project_generation.py`, `desktop/project_profile.py`, `desktop/project_rules.py`, `desktop/project_experience.py`: generation, profiles/fallback, skill grouping, reports and specialty durations.
- `desktop/test_general_quality.py`, `desktop/test_project_quality.py`, `desktop/test_project_profile.py`, `desktop/test_project_edition.py`: cross-domain, ownership, fallback, export and compatibility checks.
- `desktop/fixtures/salesforce-jd.txt`, `desktop/fixtures/java-jd.txt`, `desktop/fixtures/qa-jd.txt`: acceptance fixtures.
- `desktop/build_projects.ps1`, `desktop/project_installer.nsi`: regression coverage, native exit handling, release 1.4.0 and installer backup.
- `README.md`, `desktop/README.md`, `desktop/PROJECT_EDITION.md`, `docs/DESKTOP_TECHNICAL_OVERVIEW.md`, `docs/DESKTOP_INSTALLATION.md`, `docs/DESKTOP_REQUIREMENTS.md`: documentation.
- `desktop/MAC_HOSTING_PHASE2.md`, this document: deferred hosting decisions, measured results and remaining gates.

Earlier uncommitted work already present in this workspace is preserved. `build/` and `dist/` remain ignored; generated candidate documents, model weights and installers were not added to Git.
