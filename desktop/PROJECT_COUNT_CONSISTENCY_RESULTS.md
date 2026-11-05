# Project Edition 1.6.6 - consistent JD experience and job binding

## Confirmed causes and correction

Version 1.6.5 missed Markdown labels such as `**Experience:** 8+ Years`, minimum/required wording and several adjective chains. It then selected the default three-project tier. Separately, `Window.input_changed` overwrote the displayed document's JD without changing its original generation policy or requirement brief. Saved drafts demonstrated both problems, including a previous job's experience passage absent from its newly saved JD.

Version 1.6.6 normalizes a parsing view of Markdown, Unicode whitespace/dashes, bullets, labels and multiline fields while preserving raw evidence passages. Overall and specialty scopes remain separate. The shared JD brief supplies one experience/count decision to planning and the summary. Ranges use their lower bound, conflicting explicit totals select their highest value with warnings, and unrelated dates, retention, contracts and onboarding milestones are excluded. Unrecognized experience wording produces review warnings.

Project tiers remain **3 below eight overall JD years or missing, 5 at eight to below twelve, and 6 at twelve or more**. Source experience and default career totals do not choose the tier. JD experience continues to take priority for the generated summary.

Each new job stores a versioned immutable generation context with job ID, submitted-JD fingerprint, resume path and project policy. Worker-injected job IDs and copied queue payloads prevent cross-job relabelling. Completion verifies structured and rendered project counts before declaring success; incomplete work remains separately recoverable.

Pasting a subsequent JD stores a comparison JD, not a replacement generation JD. HTML comparisons rebuild the appropriate requirements, experience and evidence ledger; they distinguish the saved generation target from the comparison target. Generate uses the current form JD. Pending form inputs are saved separately, including the resume path, and survive restart. A completing job saves edits to the preceding resume before displaying its result. Historical inconsistent drafts are flagged rather than rewritten or expanded.

No model, generation stage or interface button was added. Full fictional generation of experience, projects, skills, certifications and metrics remains enabled. The current model, six summary bullets, three/five/six detailed project blocks, seven responsibilities per project, date-free format, confidential headings, Role metadata, memory safeguards, 4,096-token context, 768-token output budget and 27-submission ceiling remain. Cosmetic and technical checks continue to assess completeness and internal consistency rather than source truth.

## Regression and final frozen-worker verification

**305 regression checks passed**, including equivalent plain/Markdown forms at the 7/8/12-year boundaries, decimals, ranges, conflicts, specialties, unfamiliar named specialty scopes, ambiguous wording and excluded non-career numbers. An additional repeat of the GUI scenario passed after strengthening its late-edit assertion. Existing full-stack, Salesforce, Java, Databricks, AWS, Azure, QA, field-leak, export and legacy matching checks remain included.

The GUI scenario exercised changing a JD after completion and during generation, one waiting job, immutable payload copies, stale-event rejection, pending source/JD restoration, preservation of late edits, undo/redo and autosave/restart. It used isolated data and a process-start stub for deterministic queue coverage. The final frozen GUI also restored that state and exited successfully.

Three fresh cold-model generations then ran through the source Qt GUI/controller and the **final frozen 1.6.6 worker** on Windows, Intel i5-13450HX, 16 GB RAM, RTX 3050 6 GB. All used a synthetic candidate claiming 20 years to verify JD independence. Times cover Generate through editable preview and autosave, including startup and bounded repairs. Each is one observation, not a repeated-run median or a promise for other hardware.

| Fixture | JD overall years | Actual projects | Seconds | Actual calls including retries/repairs | Peak app-tree RSS GiB | Peak device GPU MiB | Mandatory evidence supported/partial/missing |
|---|---:|---:|---:|---:|---:|---:|---|
| project-count-cloud | 6+ | 3 | 82.670 | 15 | 2.986 | 4668 | 1/1/0 |
| project-count-snowflake | 8+ | 5 | 87.817 | 18 | 3.001 | 4338 | 2/1/0 |
| project-count-data | 12+ | 6 | 109.330 | 21 | 2.997 | 4348 | 1/2/0 |

All runs completed within 300 seconds, preserved their submitted JD fingerprints, included six summary bullets and seven responsibilities per project, and remained within token/request budgets. All extracted named mandatory/preferred skills were included in Technical Skills. RSS is sampled resident memory, not total system commit; GPU readings are device-wide and include other software. These tests do not qualify an 8 GB laptop, CPU-only timing, Mac hosting or every GPU.

The final frozen worker verified all **161 pinned assets** offline and produced original plus edited DOCX/HTML pairs for each tier (**12 exports**). Checks verified project counts, distinct titles, date removal, confidentiality headings once per block, no redundant company row, Role fields, exact named skills and edited export authority. A separate frozen comparison exported HTML and DOCX from the three-project result against the twelve-year JD: the report correctly showed a six-project comparison target while the DOCX retained its three edited projects. Submitted and comparison JD sections were labelled separately.

Owned-process cancellation acknowledged in 0.0079 seconds; no owned process remained after 750 ms. No installed application/model was terminated. Testing used isolated data; saved user resumes and the installed app were not modified.

## Remaining review items

Skill inclusion is separate from project implementation evidence. The table and each HTML report expose partial/missing facets, metric-context warnings and summary review notes. These heuristic observations are not an external ATS score, verified professional history or a guarantee of 100% implementation coverage. Fictional professional claims remain enabled. Clean-machine installation/upgrade/uninstall and physical network-disconnected testing were not repeated; frozen asset verification and execution used offline settings and bundled assets.

## Delivery and update instructions

The new installer is `C:\Games\Resume Builder Application\ResumeOptimizerProjectsSetup-1.6.6.exe`. Close Project Edition, run it and keep the existing installation directory `C:\Users\prati\AppData\Local\Programs\ResumeOptimizerProjectEdition`. Installation is a separate user action. Saved drafts are preserved: generate a fresh resume to apply the new parsing policy. Version 1.6.5 remains in the same installer folder for rollback. Back up `%LOCALAPPDATA%\ResumeOptimizerProjectEdition` before upgrading.

Source is at `C:\Users\prati\source\Resume-Builder`, outside OneDrive, on branch `FinalVersion2.0`. Build with the documented pinned dependencies/assets, `desktop/build_projects.ps1` and NSISBI. Installer weights, local data and build artifacts are ignored by Git. The adjacent installer checksum/manifest identify the exact binary and rollback hash.

Local evidence: `build/final-suite.log`, `build/final-bundle.log`, `build/acceptance/real/`, `samples/`, `quality-details.json`, `frozen-binding/`, `ui-data/ui-check.json`, `ui-data/logs/gui-startup.json`, and `cancel/checks.json`. New regression fixtures contain role/technology requirements, not candidate personal data.

The changes cover JD experience/policy/brief handling, immutable job binding, controller/UI snapshots, comparison-aware reports/exports, completion validation, worker job association, versioned packaging and regression/release documentation. Existing model assets and the installed application are untouched.
