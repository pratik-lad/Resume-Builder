# Project Edition 1.6.4 — release verification

## Changes and compatibility

New resumes select project count from the JD's explicit **overall** experience: **3 below 8 years or missing; 5 at 8 to below 12; 6 at 12+**. Ranges use their lower bound. Conflicting totals select the highest explicit total with a report warning. Source experience, specialty durations and the default career total never select the tier.

Planning uses batches of at most three, unique role identifiers and count-aware fallbacks. Each project retains its overview, metadata, five technical and two functional responsibilities. All projects contribute to summary context. Six summary bullets, the current model, full fictional generation, date removal, confidential headings and Role fields remain. The company metadata row is still omitted. No hosting, memory-control or GPU-behavior changes were made.

The base workflows use 11/16/18 calls for 3/5/6 projects. The existing three shared malformed-response retries, two shared quality-repair submissions, 4,096-token context, 768-token output limit and 27-request ceiling remain. Required remaining calls are reserved before optional work. Separately saved incomplete snapshots identify completed/expected counts and cannot overwrite the last saved resume. Existing drafts and edited export text remain authoritative; removed projects are reported, never restored silently.

## Real generation measurements

Measured on Windows, Intel Core i5-13450HX, 16 GB RAM and RTX 3050 6 GB, using the unchanged pinned Qwen3-4B-Instruct-2507 Q4_K_M and CUDA runtime, with all 37 reported layers offloaded. This is not an 8 GB reference-laptop or CPU benchmark.

Four domains (full-stack, AWS Cloud Engineer, Databricks, Forward Deployed AI Engineer) were each run at 7, 8 and 12 overall JD years. A synthetic source resume stated 9+ years, intentionally checking that a higher source total does not raise the project tier. Each result is one fresh cold-model run. Times include worker/model startup, generation, review, editable preview and autosave; exports are separate. These observations do not establish repeated-run medians or performance on other hardware.

| Projects | Median seconds across four domains | Range seconds |
|---|---:|---:|
| 3 | 72.005 | 68.052–78.514 |
| 5 | 97.209 | 92.395–105.128 |
| 6 | 113.327 | 106.438–119.117 |

| Fixture | Projects | Seconds | Calls including retries/repairs | Peak app tree RSS GiB | Peak device GPU MiB | Mandatory evidence supported/partial/missing |
|---|---:|---:|---:|---:|---:|---|
| full-stack-p6 | 6 | 115.750 | 20 | 2.989 | 4127 | 15/6/1 |
| full-stack-p3 | 3 | 68.052 | 13 | 2.991 | 4025 | 13/8/1 |
| full-stack-p5 | 5 | 93.276 | 18 | 2.999 | 4013 | 16/5/1 |
| aws-p3 | 3 | 68.454 | 13 | 3.009 | 4038 | 13/7/3 |
| aws-p5 | 5 | 101.141 | 18 | 2.988 | 4069 | 12/5/6 |
| aws-p6 | 6 | 106.438 | 20 | 2.993 | 4055 | 7/11/5 |
| databricks-p3 | 3 | 78.514 | 14 | 3.003 | 4119 | 9/12/1 |
| databricks-p5 | 5 | 105.128 | 18 | 3.007 | 4115 | 10/11/1 |
| databricks-p6 | 6 | 119.117 | 20 | 2.989 | 4244 | 10/11/1 |
| forward-ai-p3 | 3 | 75.557 | 15 | 3.008 | 4033 | 5/21/3 |
| forward-ai-p5 | 5 | 92.395 | 18 | 2.994 | 4071 | 4/18/7 |
| forward-ai-p6 | 6 | 110.903 | 20 | 3.001 | 3832 | 9/15/5 |

All 12 uncontended runs completed below 300 seconds. Peak app-tree RSS was at most 3.009 GiB. This is sampled resident memory, not total system commit or a guaranteed memory cap. GPU readings are device-wide and include allocations outside this app; peak was 4,244 MiB. The largest actual rendered input was 2,417 tokens, leaving room for the 768-token output budget inside 4,096. Maximum sampled GUI event-loop gap was 0.068 seconds.

All generated documents had the selected count, distinct titles, seven responsibilities per project, six summary bullets, and every extracted named mandatory/preferred tool in Technical Skills. Eleven samples used model-written summary halves; Forward-AI/3 used the existing structured fallback after bounded retries. Actual submissions were 13–20, including up to two quality repairs. No extra model stage or model change was introduced.

One earlier Databricks/6 attempt was cancelled automatically when the installed app started its model. It is excluded from timing statistics and retained as an explicit interruption, with a separately saved incomplete 5-of-6-project snapshot. The replacement run completed. A later Forward-AI/6 run stopped before saving its final result during the usage interruption and was rerun; that unfinished observation is not counted as success.

## Verification

- **237 regression checks passed**, including boundaries, decimals, ranges, conflicts, YOE/yrs/bare headers, specialty-only and missing requirements, source independence, calendar/logistics exclusions, all project tiers, request reserves, recovery and edited reports. The suite includes existing full-stack, Salesforce, Java, Databricks, AWS, Azure and QA checks, plus legacy matching/catalogue checks; real inference was limited to the four domains above.
- The final frozen worker verified all 161 pinned bundled assets offline, then exported 12 original DOCX/HTML pairs and 12 edited DOCX/HTML pairs. Named-skill presence, no calendar dates, confidential headings appearing once per project, Role metadata and absence of generated employer names passed. Explicitly edited skills remained changed; exports reported missing skills instead of restoring them.
- Interactive Qt checks covered editing, preview refresh, undo/redo, six-project autosave recovery and final frozen GUI startup/clean exit. Measured edit insertion: 0.0006 seconds; frozen startup including the deliberate 1.5-second self-close: 4.306 seconds. These are automation observations, not a complete manual UX review.
- Final frozen-worker cancellation acknowledged in 0.0075 seconds; no owned worker/model PID remained after 750 ms. No unrelated app/model was terminated.
- Representative full-stack DOCX pagination was rendered through Word for visual review: 3 projects / 4 pages, 5 projects / 6 pages, 6 projects / 6 pages. Review PDFs are temporary test artifacts, not an added PDF-export feature.

The inference benchmark bundle preceded only the final HTML project-count display and invalid calendar-header guard. The final source suite, frozen export/UI/cancellation checks and final fixture-policy comparison validate those changes; normal acceptance prompts and selected counts are unchanged.

## Remaining quality items and limits

Named-skill inclusion is **not** demonstrated implementation or an ATS score. The table reports capability evidence separately. Existing heuristic checks still identify partial/missing capability facets, metric measurement conditions/windows and occasional summary-length warnings. These are visible in each HTML report and the skill/evidence CSV. No subjective quality percentage, guaranteed 100% evidence coverage or external ATS score is claimed. Full fictional professional claims remain enabled and are not measured application results.

Clean-machine installation/upgrade/uninstall, physical network-disconnected operation, 8 GB hardware, CPU-only timing and Mac hosting were not requalified in this update. The final worker uses offline flags and bundled assets; the installed app and saved user data were left untouched. Installation remains a separate user action.

## Delivery and rollback

After packaging, use `C:\Games\ResumeOptimizerProjectsSetup-1.6.4.exe` and its adjacent SHA-256 file. Close Project Edition and choose the existing `C:\Games\ResumeOptimizerProjectEdition` folder. Back up `%LOCALAPPDATA%\ResumeOptimizerProjectEdition` before upgrading. Keep `C:\Games\ResumeOptimizerProjectsSetup-1.6.3.exe` for rollback; it is preserved. Saved drafts are not expanded automatically: generate a fresh resume to use the new tier.

Local evidence is under `build/project-counts`: `measurements.json`, `final-samples/` (DOCX, HTML and skill/evidence CSV), `ui/results.json`, `cancel/results.json`, and the real-run folders. Final build log: `build/project-count-final-bundle.log`; regression log: `build/project-count-release-suite.log`. The installer manifest records hashes, pinned model and rollback artifact. Installer and model assets are ignored build outputs; source edits have not been pushed automatically.

## Changed source files

- `desktop/project_policy.py`, `project_experience.py`: JD-only tier and scoped duration parsing.
- `desktop/project_generation.py`, `generation.py`, `project_profile.py`: batched planning, variable counts, all-project context, request reserves and recoverable work.
- `desktop/project_rules.py`: dynamic checks and edited-count reporting.
- `desktop/test_project_counts.py` and existing project/profile/quality fixture helpers: regression coverage.
- `desktop/gui_benchmark.py`, `verify_skill_release.py`: real timing and count-aware frozen exports.
- `desktop/build_projects.ps1`, `project_installer.nsi`: tests and installer version 1.6.4.
- `README.md`, desktop documentation, this report, `docs/DESKTOP_INSTALLATION.md`, `docs/DESKTOP_REQUIREMENTS.md`: behavior, rebuild, installation and verification instructions.
