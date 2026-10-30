# Project Edition 1.6.3

Workspace cleanup: obsolete local builds and rollback installers were removed at the user's request on 29 October 2026. The current app, installer, selected model, source and update tools remain. See [workspace maintenance](../docs/WORKSPACE_MAINTENANCE.md); historical rollback paths below no longer apply.

This version includes explicit JD skill coverage and uses one confidential company heading per project. See [verification and remaining limitations](SKILL_COMPLETENESS_RESULTS.md). The strict no-slowdown gate has not passed. The reference layout, full fictional generation, existing model and saved drafts are preserved. Earlier model and runtime measurements remain in [the reference verification](QUALITY_REFERENCE_RESULTS.md).

The general quality update is documented in [PROJECT_EDITION.md](PROJECT_EDITION.md)
and [GENERAL_QUALITY_RESULTS.md](GENERAL_QUALITY_RESULTS.md). New summaries use
complete bullets with a bounded local fallback. Relevant certifications use an
offline ranked catalogue. Project scopes follow the JD rather than fixed domain
recipes. The new 2.50 GB Qwen3-4B-Instruct-2507 model replaces the 2B model.
See [model upgrade results](MODEL_UPGRADE_RESULTS.md). The removed 2.3 GB startup
gate stays removed; the running 4 GiB cap remains. Build this larger installer with
the pinned NSISBI compiler described in the installation guide.

The following sections also document the original desktop edition and historical releases.

# Resume Optimizer Desktop (Windows x64)

For the current **Project Edition 1.6.3**, follow
[installation](../docs/DESKTOP_INSTALLATION.md) and
[requirements](../docs/DESKTOP_REQUIREMENTS.md). Its entrypoint is
`desktop/project_main.py` and installer is `ResumeOptimizerProjectsSetup.exe`.
The instructions below describe the preserved legacy desktop edition.

The desktop version runs entirely on the laptop. Its native editor and worker
do not require Docker, n8n, Python, an account, or an internet connection on the
target machine. The installer includes Qwen3.5-2B Q4_K_M, the BGE INT8 embedding
model/tokenizer, native CPU llama.cpp, Python/Qt, and the document renderer.

## Use

1. Run `dist/ResumeOptimizerDesktopSetup.exe`, then open the desktop shortcut.
2. Select a text-based PDF or DOCX and paste the job description.
3. Select **Generate resume**. The model writes the complete resume in the background.
4. Review the finished preview. Select **Edit resume** to change a section; edits
   are autosaved and support undo/redo. Select **Done editing** to return to preview.
5. Save DOCX and HTML report. Both exports use your current edits; report coverage
   is recalculated in the background.

Generation always permits invented work experience, skills, projects,
certifications and metrics. Name, contact details and education are preserved
from the upload. There is no source-only mode, fast-draft selection or separate
polishing button. Previously saved drafts remain readable.

Quality comes before latency. The complete resume uses 19 bounded model calls
before any validation repairs; completion may take several minutes. Each project
includes metadata, at least eight technical and three functional responsibilities.
Projects explicitly describe the business problem, architecture, data flow,
evaluation, deployment, security controls and measurable outcome. Missing project
evidence is checked locally and reported without extra model calls.
Version 0.3.1 allows one validation retry per section, at most three retries
across the resume, and at most two optional duplicate-replacement calls
(19 initial calls; at most 24 generation submissions). Validation retries vary
the sampling seed. Evaluation wording and punctuation are normalized locally;
inconsistent numeric baselines remain visible as HTML review notes. Required names omitted from categorized skills are filled from the JD;
this does not count as experience or project evidence.
Project metadata, descriptions and design fields use separate small requests to
avoid incomplete fields; structural completeness and team sizes are validated.
Cosmetic project-design checks no longer discard a completed project.
The sample documents guide organization and detail, not candidate identity.
Validated sections are cached locally; version 0.3 uses a new cache namespace.
Employment/project dates are omitted from generation, preview, restored drafts
and exports. Education dates and experience-length statements remain intact.
There are no calendar-based tool restrictions or added confidential labels.

The HTML report separates required-skill keyword presence, experience/project
narrative evidence and project-only evidence, with passages and remaining gaps.
Evidence requires an action/mechanism passage of at least twelve words; a tools
list alone does not count. These reproducible text checks are not an ATS score,
technical correctness guarantee, or proof of fictional qualifications.

There is no minimum-free-RAM startup gate. Generation uses at most four physical CPU
threads, below-normal priority, one model slot and 4,096-token context. Each call
uses a logical prompt batch of 256 and a microbatch of 64 to limit working memory,
and reserves at most 768 output tokens and counts its rendered prompt. Large JDs are
condensed to local extracted requirements for generation; the complete JD is
retained for the report. Keep important requirements near the beginning of
unusually large JDs, and check final report coverage.
No GPU driver is needed. Expect at least 5 GB free disk for installer and app.

Scanned PDFs need conversion to a text PDF or DOCX first. OCR is not included.

## Data and lifecycle

Installed files: `%LOCALAPPDATA%/Programs/ResumeOptimizerDesktop`.
Drafts, settings, artifacts, and logs: `%LOCALAPPDATA%/ResumeOptimizerDesktop`.
The application has its own identity and allocated private model port, separate
from ResumeOptimizerCopy. Closing or cancelling kills only its owned workers
and model. Windows job objects also clean up children if the GUI crashes.
An unused model unloads after five minutes.

Upgrades overwrite installed application files and preserve user data.
Uninstall also preserves user data. Copy the user-data folder to back up drafts;
export files saved elsewhere must be backed up separately.

## Build from source

Development needs Windows x64, Python 3.11, internet for asset preparation,
and the free NSIS compiler. Target users need none of those build tools.

```powershell
.\desktop\build.ps1
# Or supply a portable NSIS compiler:
.\desktop\build.ps1 -NSISCompiler C:\tools\nsis\makensis.exe
```

The build installs pinned dependencies in `desktop/.venv`, verifies pinned
asset hashes, runs desktop regression tests, freezes a directory bundle,
and builds `dist/ResumeOptimizerDesktopSetup.exe`. Each build uses a fresh portable bundle folder; `build/desktop-latest.json` records its location. If running the portable version, copy that bundle to a short path such as `C:\ResumeDesktop` first: deeply nested checkout paths can exceed Windows DLL path limits. Build/download artifacts
are ignored by Git. To develop without rebuilding:

```powershell
.\desktop\.venv\Scripts\python.exe desktop\main.py
```

Workers communicate using NDJSON over inherited pipes. Every event contains
`job_id`, `stage`, and `status`; successful jobs include a result, failed jobs
include a message. One job may run and one may wait. The completed resume appears only after generation and validation finish; a failed or cancelled job preserves the previous saved resume.

## Verification

```powershell
.\desktop\.venv\Scripts\python.exe -m pytest desktop\test_desktop.py desktop\test_generation.py -q
.\desktop\.venv\Scripts\python.exe desktop\smoke.py
.\desktop\.venv\Scripts\python.exe desktop\gui_smoke.py
# UI-only check without loading the model:
.\desktop\.venv\Scripts\python.exe desktop\gui_smoke.py --no-model
python desktop\validate_embeddings.py
.\desktop\.venv\Scripts\python.exe desktop\install_smoke.py
```

The embedding validation command uses the existing development environment with
sentence-transformers and its cached BGE model. PyTorch is excluded from the
desktop bundle. Benchmark outputs live in `build/desktop-*.json`.
See TEST_RESULTS.md for actual results and outstanding release qualification.

This is an unsigned development build. Windows may identify its publisher as
unknown. Third-party notices are under `_internal/desktop-assets/licenses`;
application source is supplied under `_internal/source`. See THIRD_PARTY.md.

The owned llama-server disables its auxiliary RAM prompt cache (`--cache-ram 0`);
its default 8 GiB cache is incompatible with the desktop 4 GiB budget.
The active 4,096-token inference context is retained.

Version 0.3.2 skips empty/malformed AI skill entries, keeps short names such as
C#, Go and R, and fills missing JD skills locally. Empty skills never restart
the entire resume. Other sections retain their existing validation limits.

Project title/client collisions, person-like titles and team-size formatting
are repaired locally instead of restarting generation. Client names stay named.
