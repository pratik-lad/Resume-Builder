# Project Edition 1.2.0 — Phase 1 verification

Updated 24 October 2026. Full fictional professional generation remains enabled.
User acceptance of output quality is required before Phase 2 starts.

## Implemented

- Six substantial professional-summary bullets written after project repairs;
  distinct profile topics and controlled professional openers, not copied tasks.
- JD target role and numeric experience: explicit resume total, then JD lower
  bound, then 9+ years. No calculation from calendar dates.
- Bold, JD-specific skill categories containing tools and implementation concepts.
- Target Role and Contribution metadata, meaningful project titles, scoped
  responsibilities and repairs that cannot increase known technical warnings.
- Fresh generation seeds/cache identities; JD-relevant certification candidates
  without a mandatory fixed trio. Relevant certifications can still recur.
- Schema-6 date policy removes body calendar dates, including education dates,
  while retaining qualifications, contact details and experience durations.
  Old drafts retain their date policy. Edited text remains export authority.
- Formatted, escaped HTML report; mandatory/preferred keyword counts are separate
  from project evidence. Unmapped requirements and qualifications need manual review.
- Known technical checks include Delta storage versus DynamoDB session/log
  coordination, inconsistent metrics, unclear units, mixed clouds and repetition.
- 21 normal section calls, up to two single-shot project repair calls and three
  shared validation retries; hard guard remains 27. CPU/model/RAM settings unchanged.

## Automated and interface checks

Regression checks cover all three repository JDs (Databricks, AWS, Azure GenAI),
repeated generation identities, cache isolation, bounded retries, summary style,
implementation concepts, certifications, date policies, rendering, escaping,
editing, undo, autosave, cancellation and legacy coexistence. Final build results
and release checksum are recorded in the build manifest.

Final build regression run: **95 passed**, five existing PyMuPDF/SWIG
deprecation warnings, 76.86 seconds on this busy development host. An earlier
run of the same suite took 125.91 seconds while model inference was active.

An isolated offscreen Qt check using a fake model passed editing/preview/autosave
with a 1.1 ms edit handler and 12.7 ms preview/autosave. Its generation duration
and memory are not model benchmarks.

## Real-model iteration 1

- Synthetic candidate with an explicit 5+ years statement and repository Databricks
  JD (684 words), isolated source GUI and worker, bundled Qwen3.5-2B Q4_K_M.
- Generation: 429.199 seconds, 25 model submissions.
- Peak GUI/worker/model RSS: 2,356,314,112 bytes (2.19 GiB).
- Edit handler: 1.8 ms; preview/autosave: 19.1 ms; maximum event-loop gap: 112.1 ms.
- Cancellation acknowledgement after generation: 10.4 ms. This does not measure
  interruption during active inference; process cancellation has separate tests.
- No runtime errors. A preceding attempt was blocked by the unchanged free-RAM
  startup check; it did not generate a resume.

Review of this iteration prompted stricter profile fields, ownership-scoped repairs
and technical guidance. These timings are for that iteration, not a promise for
the final workflow or an 8 GB laptop.

## Real-model iteration 2

- Frozen worker with source Qt harness, fresh Databricks generation: 448.941
  seconds, 23 submissions, 2,339,913,728 bytes peak RSS (2.18 GiB).
- Edit handler 0.5 ms, preview/autosave 12.2 ms, maximum event-loop gap 88.0 ms.
- The three planned titles differed from iteration 1. Certification variation is
  evaluated for relevance; relevant titles are allowed to recur.
- This review motivated project-specific system guidance, unambiguous generated
  units and grammatical summary continuations. Final measurements follow below.

## Final reference sample and release checks

- Windows x64 build 26200, approximately 16 GB RAM (15.71 GiB available to the
  OS), 10 physical CPU cores; llama.cpp limited to four CPU threads, GPU off.
- Fresh isolated Databricks run with a frozen worker and source Qt harness:
  **501.321 seconds (8 min 21 sec), 25 model submissions, 2,387,951,616 bytes
  peak GUI/worker/model RSS (2.22 GiB)**. Tests and installer compression
  overlapped part of the run. This is not an 8 GB reference-laptop result.
- Edit handler: 1.4 ms; preview/autosave: 22.0 ms; maximum event-loop gap:
  156.4 ms. These are observed development-host measurements, not universal
  responsiveness guarantees.
- Raw summary fields were replayed locally through the final prefix normalizer
  without additional model calls or manual rewriting of claims. The per-half
  topic instructions were narrowed after this run; a complete generation using
  that final prompt wording has not been timed separately.
- Final packaged worker exported the sample DOCX in 3.914 seconds and HTML in
  3.791 seconds, then verified bundled asset checksums in 2.230 seconds.
- DOCX/HTML checks passed for six summary bullets, bold skill labels, three
  target-role/contribution metadata blocks, client masking and absence of the
  source education year. The sample uses a synthetic identity, not the user's
  unavailable previous candidate attachment.
- Active planning cancellation with the final worker: **9.97 ms** to acknowledge,
  four owned processes before cancellation, zero still running after 500 ms.
  The llama.cpp log confirmed active slot/prefill activity.
- Native packaged GUI launched with Python removed from the test PATH. Final
  packaged generation/export module source copies match the checkout.

### Observed coverage, not an ATS score

| Local check | Reference sample |
| --- | --- |
| Mandatory named keywords | 23 / 23 present |
| Preferred named keywords | 3 / 5 present |
| Mandatory capability evidence | 7 supported, 18 partial, 1 missing |
| Preferred capability evidence | 1 supported, 4 partial, 1 missing |
| Unique project titles / six bullets per project | Pass / Pass |
| Additional Capabilities fragment insertion | Absent |

"Supported" requires all locally configured facets, with passages in the report.
These denominators differ from the named-technology narrative-evidence table.
They do not measure an external ATS or verify invented experience. **This sample
does not establish the requested 95%+ implementation-evidence target.** Remaining
partial requirements, profile tool-name warnings and two known technical warnings
remain visible in the HTML report. Project title/ownership alignment and cloud
authentication boundaries still warrant human review.

### Installer

- `dist/ResumeOptimizerProjectsSetup.exe`, version **1.2.0**.
- Size: **1,402,867,923 bytes** (approximately 1.31 GiB).
- SHA-256: `1dfddb0b2e7ae37e76fc777d858e26145581ce7551a358c1f9d024e046afa77b`.
- Prior local setup EXEs remain under `dist/ResumeOptimizerProjectsSetup-backup-*.exe`.
- The installer was rebuilt; a clean-machine installation/upgrade/uninstall cycle
  was not performed during this phase. Packaged launch, worker generation,
  exports, assets and cancellation were checked locally.

## Files changed

- Generation: `project_generation.py`, new `project_profile.py`, `generation.py`,
  `project_rules.py`.
- Presentation/export: `project_document.py`, `quality.py`, `draft.py`.
- Tests/build: new `test_project_profile.py`, `test_project_quality.py`,
  `test_project_edition.py`, `gui_smoke.py`, `build_projects.ps1`,
  `project_installer.nsi`.
- Documentation: root `README.md`, `PROJECT_EDITION.md`, this report,
  `docs/DESKTOP_INSTALLATION.md`, `docs/DESKTOP_TECHNICAL_OVERVIEW.md`.

Paths without a directory prefix above are under `desktop/`. Downloaded assets,
samples, virtual environment and installers are ignored build artifacts. No
original candidate document or secret was added to source control.

## Release gates and limitations

- Review files: `build/phase1/Databricks_sample.docx` and
  `build/phase1/Databricks_sample.html`; measurements and raw/normalized sample
  records are in the same ignored directory.
- Actual 8 GB reference hardware, physically disconnected clean Windows installation
  and true upgrade from an earlier installed release remain separate release gates.
- Local textual checks cannot prove architecture correctness or factual claims.
  Missing/partial evidence and technical warnings must be reviewed; no external
  ATS score or guaranteed 95% result is claimed.
- Current checkout had no earlier installer. The build preserves its previous
  local setup EXE as a backup when replacing it; that backup may be a 1.2.0
  intermediate build rather than a previously released 1.1.0 installer.
- Phase 2 (RAM policy changes, Mac/Metal hosting, automatic startup and tunnels)
  is deferred. The 2.3 GB startup check and 4 GiB runtime cap are unchanged.


## 1.2.1 correction ? remove free-RAM startup block

At the user?s request, removed the fixed 2.3 GB free-memory requirement from
model startup. The earlier measurements above describe 1.2.0. There is no
replacement free-memory threshold. The separate 4 GiB running-process cap,
context limits and cancellation behavior remain unchanged. Replaced the old
low-memory rejection test with a check that startup reaches process creation
even with only 100 MiB free. The 1.2.1 installer retains saved user data.

Correction build verified: 94 tests passed (89.92 seconds); five existing
SWIG deprecation warnings. Installer version 1.2.1, 1,402,868,284 bytes.
SHA-256: `a00ba376ca6afd9a75d6d37ab444e50b52dcadf04448830fb88e5d177e297186`.
Packaged runtime source hash matches the updated source. Previous installer
was copied to a rollback file by the build script. No new generation benchmark
was needed for removal of the startup check.
