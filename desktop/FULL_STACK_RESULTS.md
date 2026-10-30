# Project Edition 1.3.0 - full-stack quality verification

Updated 24 October 2026. Fully fictional generation remains enabled. No external
ATS score is claimed; fictional durations and qualifications are not verified.

## Implementation

- Separate versioned overall/specialty duration profile; choose the higher
  explicit source/JD total, keeping specialty lower bounds independently.
  Defaults to 9 only when no overall total is stated. A specialty exceeding the
  overall total raises the fictional total and leaves a review warning.
- Source 5+ overall plus JD 8+ software/5+ full-stack produces 8+ overall and 5+
  full-stack. No calendar arithmetic or employment dates are introduced.
- Six project-led summary bullets, bold categorized skills, three visible
  employers and date-free Relevant Project Experience. Client masking remains
  Confidential client. Existing saved drafts are not migrated or rewritten.
- Python/React full-stack project ownership: application engineering,
  requested GenAI integration, and application production delivery. Scoped
  prompts ask for React state/forms/errors, backend transaction boundaries,
  pytest/Jest evidence, reviewed AI coding workflows and incident ownership.
- The assigned AI coding tool is included without automatically copying every
  example from the JD. Frontend, backend and cloud authentication are separated.
- Generation normalizes recurring subject/verb summary fragments into grammatical
  continuations. LLM integration is separated from authentication, and Copilot
  assistance is separated from configured CI security/lint checks. Edited text
  is reported without those generation-only rewrites.
- Summary context now includes evaluation/test bullets. Export checks re-read
  edited text; stale generated metadata cannot satisfy duration requirements.
- HTML reports separate experience requirements, mandatory/preferred keyword
  presence, capability passages, technical warnings and unconfirmed logistics.
  Known storage/authentication issues produce review warnings, not assertions
  that arbitrary architectures are correct.
- Quality rule revision projects-quality-8 and profile revision project-profile-3
  invalidate affected generation requests. Per-generation seeds/cache identity,
  two quality-repair calls and the hard 27 logical-submission limit remain.
- The 2.3 GB startup block remains removed. The separate 4 GiB runtime cap and
  existing CPU/context limits remain. Mac hosting/Phase 2 is deferred.

## Verification

Final source regression suite: **117 passed**, five existing PyMuPDF/SWIG
warnings, **75.38 seconds**. Databricks, AWS, Azure GenAI and full-stack fixtures
cover domain isolation, experience parsing/ranges/order/conflicts, profiles,
cache identities, bounded repairs, skills, edited reports, old drafts, date
removal, DOCX/HTML exports, undo/autosave, cancellation and separate app identities.

Final packaged GUI launched successfully with Python removed from PATH using
an isolated data profile. Startup/self-close completed in 2.47 seconds with the
window initialized; this is not a clean-machine installation measurement.

Active-inference cancellation on the final packaged worker: 15.6 ms acknowledgement;
four owned processes before cancellation, none remaining after 500 ms. It used
an isolated profile and did not terminate another application's process.

## Real-model iterations

Host: Windows 11 x64, Intel Core i5-13450HX, 10 physical cores/16 logical CPUs,
approximately 16 GB RAM. Inference uses four CPU threads and no GPU. This is not
the required 8 GB reference laptop. Model remains bundled Qwen3.5-2B Q4_K_M
through the pinned Windows llama.cpp CPU runtime. No external AI API is used.

Input: local sample-resume.pdf, five pages, with the exact supplied Senior
Full Stack Developer JD (152 words). Identity and BTech/college/CGPA were parsed
successfully. Detected contacts are empty because this PDF has no parsed contact
strings. The input document was not modified or copied into the repository.

First source iteration: 452.05 seconds, 25 logical submissions,
2,305,900,544 bytes peak GUI/worker/model RSS (2.15 GiB). Correct 8+/5+ experience
but partial frontend/testing evidence and technical warnings prompted the final
scoped instructions, test-aware summary brief and metadata tool normalization.
Tests/build activity overlapped this iteration; it is not the release benchmark.

A packaged acceptance attempt exposed a summary-validator bug: after a malformed
response used the available section retry, a valid response with a quality
warning could still abort. The corrected Writer exposes the current validation
attempt; quality-only retries cannot reject an otherwise usable final response.
The new regression exercises malformed-then-valid-with-warning behavior.
That failed attempt is not reported as a successful generation benchmark.

## Final packaged generation and exports

The final bundle (project-profile-3, projects-quality-8) generated a fresh
resume from the supplied PDF and JD with **no runtime errors**:

| Measurement | Observed |
| --- | --- |
| Full generation | 462.559 seconds (7 minutes 43 seconds) |
| Logical model submissions | 25 (hard ceiling 27) |
| Peak sampled GUI/worker/model RSS | 2,311,479,296 bytes (2.15 GiB) |
| Edit handler | 1.3 ms |
| Preview/autosave | 12.6 ms |
| Maximum observed event-loop gap | 115.1 ms |
| DOCX export | 0.987 seconds |
| HTML export | 1.391 seconds |
| Bundled asset verification | 1.115 seconds |

Installer compression overlapped the first portion of generation. These are
observed development-host timings, not an isolated 8 GB laptop benchmark.
The maximum heartbeat gap exceeded 100 ms, although the measured edit and
preview handlers were below 100 ms; universal responsiveness is not established.

Output checks passed: six summary bullets, three distinct project titles, six
bullets per project, three Target Role/Contribution labels, visible employers,
Confidential client, bold skill categories, and no Additional Capabilities.
Resume employment/education dates are absent. Source qualifications remain.
The 76-paragraph DOCX and HTML were built by the final frozen worker.

The resume states **8+ years overall and 5+ years full-stack**. Both appear as
stated durations in the report, not verified employment. Saved draft reload
retained the new metadata and the GUI edit. Separate edited DOCX/HTML exports
preserved an intentional 7+ overall-years edit and a custom sentence; HTML
recalculated it as below the 8-year JD requirement instead of restoring 8 from
metadata. The handoff sample remains the original unedited generated version.

### Observed coverage and remaining review items

- Recognized mandatory keywords: **11/11 present**. Preferred keywords: **3/3
  present**. These limited catalog counts do not mean every JD phrase is covered.
- Mandatory capability rows: **11 supported, 5 partial, 2 missing**. Preferred
  rows: **3 supported, 0 partial, 0 missing**. Raw JD rows can overlap the more
  specific implementation categories; do not interpret them as an ATS score.
- Of eight explicit full-stack implementation categories, **six are supported**:
  React implementation, Python/database behavior, GenAI integration,
  permission-aware retrieval, AWS production ownership, and application delivery.
- Test evidence names pytest/Jest but needs concrete fixture/mock/assertion
  detail. The AI workflow has implementation passages but needs the selected
  tool named in the passage, rather than only project metadata. Both remain
  partial after the shared two-call project-repair budget.
- Four technical warnings remain, primarily missing/comparable metric baselines
  and multiple percentage claims. Three profile review notes remain: one short
  summary bullet and two literal/alias evidence matches (API integration and
  JWT tokens). Review these in the HTML instead of assuming technical perfection.
- Location, shift acceptance and contract logistics remain unconfirmed in the
  manual-review section. No availability was inferred from the JD.

The preserved second iteration took 428.064 seconds, 26 logical calls and
2,399,506,432 bytes peak RSS (2.23 GiB); it motivated the final wording cleanup.
Its results are historical and are not substituted for this final run.

### Deliverables

- `build/full-stack/FullStack_sample.docx`
- `build/full-stack/FullStack_sample.html`
- `build/full-stack/final-document.json` and `final-measurement.json`
- `build/full-stack/output-checks.json`, `edited-export-checks.json`,
  `autosave-recovery.json`, `active-cancel.json`, `native-launch.json`
- `dist/ResumeOptimizerProjectsSetup.exe` - **1.3.0**, 1,402,910,137 bytes
- Installer SHA-256:
  `4c8b5c41d55d1fd05dbf63f4d91eeec39fca88f0f10cbef38f8f74719f3685bc`
- Verified stable 1.2.1 rollback:
  `dist/ResumeOptimizerProjectsSetup-backup-a224a6b418df40af836038857dcef375.exe`
  (its hash matches the previously supplied 1.2.1 build).

Close Project Edition, run the new installer, reopen it and generate a fresh
resume. Saved resumes are preserved. Existing drafts are not regenerated.

## Release gates and compatibility

Saved user data, installer identity and original application's separate data
location remain unchanged. The previous installer is retained by the build script.
No Git commit/push or Mac/server deployment is part of this update.

Clean disconnected Windows installation, real upgrade/uninstall on that machine,
and an actual 8 GB reference-laptop benchmark remain release gates. Local offline
mode/settings and bundled execution do not establish physical network isolation.
User review of resulting quality remains necessary; known heuristics do not verify
fictional claims or every technical combination.

## Files changed for this update

- desktop/generation.py (retry-attempt context for safe quality validation)
- desktop/project_experience.py (new duration parsing, normalization and review)
- desktop/project_profile.py (separate durations and project-led profile prompts)
- desktop/project_generation.py (scoped planning/writing and metadata)
- desktop/project_rules.py (full-stack evidence and edited experience report)
- desktop/test_project_profile.py (acceptance and regression cases)
- desktop/fixtures/full-stack-jd.txt (exact supplied JD)
- desktop/project_installer.nsi (1.3.0)
- README.md, desktop/README.md, desktop/PROJECT_EDITION.md
- docs/DESKTOP_INSTALLATION.md, docs/DESKTOP_REQUIREMENTS.md,
  docs/DESKTOP_TECHNICAL_OVERVIEW.md
- desktop/FULL_STACK_RESULTS.md (this report)

Other uncommitted workspace changes predate this update and are preserved.
