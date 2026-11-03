# Project Edition 1.6.5 - JD experience priority

## Correction

Version 1.6.4 already selected project count from the JD, but its generated career experience still used the higher of source and JD durations. A source claiming 20 years could therefore override a JD asking for 7 or 8. New generations now prioritize explicit JD overall and specialty durations, even when the source total is higher.

If the JD omits a duration, the corresponding source duration is a fallback; when neither states an overall total, the existing 9+ default remains. A source-only specialty cannot raise an explicit JD overall total. Conflicting JD overall totals still select their highest explicit requirement with a warning. Existing handling of internally inconsistent JD specialty/overall totals remains visible through warnings. Project counts remain 3 below 8 or missing, 5 at 8 to below 12, and 6 at 12+.

Experience metadata is now `experience-5` / `jd-first-overall-and-specialty`, including selection provenance. JD brief and generation-quality revisions invalidate affected generation caches. No model stage, layout change, scoring API, GPU or memory-control change was added. Full fictional generation, current model, editing, six summary bullets and seven responsibilities per project remain.

## Verification

**247 regression checks passed**, including 95 focused experience/profile checks. Tests cover higher/lower source totals, YOE, ranges, conflicting JD totals, missing durations, defaults, specialty priority, source-only specialty consistency, all three project tiers, and higher-source generation through summaries and reports. Existing cross-domain, field-leak, editing, export and legacy checks also passed.

Two fresh cold-model runs used the final frozen 1.6.5 worker on the existing Windows i5-13450HX / 16 GB / RTX 3050 laptop. Both used a synthetic source claiming 20+ overall and 15+ full-stack years:

| JD requirement | Source claim | Generated overall / full-stack | Projects | Generate-to-preview/autosave seconds | Calls including repairs |
|---|---|---|---:|---:|---:|
| 7+ overall / 5+ full-stack | 20+ overall / 15+ full-stack | 7+ / 5+ | 3 | 70.813 | 13 |
| 8+ overall / 5+ full-stack | 20+ overall / 15+ full-stack | 8+ / 5+ | 5 | 98.582 | 18 |

The generated summary, project sections and versioned experience profile followed the JD; source durations did not leak into career text. Final frozen-worker checks verified all 161 pinned assets and both original/edited DOCX and HTML pairs (8 exports), exact named skills, field roles, confidential headings and date removal. Edited skills were preserved rather than regenerated. This verifies the correction; it is not a repeated-run latency comparison or a new ATS score.

UI checks confirmed preview, editing, undo/redo and autosave recovery. A saved 1.6.4 draft with 9+ years and a 7-year JD retained its original 9+ wording and three projects: only new generation applies the new policy. Final frozen GUI startup/exit passed. Cancellation acknowledged in 0.0068 seconds with no owned worker/model PID alive after 750 ms. No installed application or saved user data was changed by testing.

Two preliminary synthetic-input checks were excluded: one lacked an Education heading, and the next placed the artificial experience statement under Education. The final acceptance source keeps career text before Education and preserves only the qualification in that section. Preliminary observations are retained separately. Implementation-evidence/metric-context warnings remain available in each HTML report. Named-skill inclusion is not proof of implementation, employment verification or an external ATS score.

## Installation and rollback

Close Project Edition, run `C:\Games\ResumeOptimizerProjectsSetup-1.6.5.exe`, and select the existing `C:\Games\ResumeOptimizerProjectEdition` installation folder. The installer is not run automatically. Back up `%LOCALAPPDATA%\ResumeOptimizerProjectEdition` before upgrading. Version 1.6.4 remains at `C:\Games\ResumeOptimizerProjectsSetup-1.6.4.exe` for rollback. Generate a fresh resume to apply the correction; existing drafts and edited exports are not silently rewritten.

Local evidence: `build/jd-experience/acceptance/`, `acceptance-samples/`, `ui/results.json`, `cancel/results.json`, `build/jd-experience-suite.log` and `build/jd-experience-bundle.log`. The adjacent installer checksum and manifest record the delivered build and rollback hashes. Clean-machine installation and other hardware were not requalified in this correction.

Changes since 1.6.4: `desktop/project_experience.py` (JD-first policy), `job_brief.py` and `project_rules.py` (revision invalidation), `project_installer.nsi` (1.6.5), experience/project-count tests, README and installation/technical documentation, and this report. Installers, model weights and local samples remain separate from the source branch.
