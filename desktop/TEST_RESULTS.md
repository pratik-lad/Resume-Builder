# Skills and metadata recovery patch 0.3.2 - 15 October 2026

## Fixed

The skills validator rejected every entry shorter than three characters,
including legitimate C#, Go, R and C names, as an "empty list entry". A blank
item anywhere also discarded the entire response.

The skills-specific normalizer keeps short names, drops blank/null/malformed or
duplicate entries, recovers delimited strings and missing category names, and
fills missing JD skill names locally. An entirely empty result with an
unrecognized JD uses a small professional-skills section with a review note.
This does not fabricate evidence or a coverage score. A constrained JSON schema
also prevents many malformed responses. Invalid JSON/transport errors retain
their existing bounded behavior.

Testing the supplied AWS JD exposed another cosmetic gate: a project title
identical to its client, or resembling a person's name, could fail the resume.
Project titles and team-size formatting are now normalized locally while
retaining client names and the generated narrative. Duplicate titles receive
distinct suffixes. Missing substantive fields still use bounded validation.

Full fabricated generation, date removal, the 19 initial / at most 24 generation
submission limit, evidence reporting and memory safeguards are retained.

## Verification

- **46 regression tests passed**: empty/null/Go skills variants produce complete
  resumes in 19 calls without retries; C#/F#/C++/Go/R/C are preserved; generic-JD
  empty-list fallback and project identity recovery are covered.
- The supplied 482-word AWS Cloud Engineer JD was tested with injected
  Python/Java/Go/blank/null entries: complete resume in 19 simulated calls with
  zero retries. The candidate source was the earlier eight-page PDF.
- Real frozen-model test on that JD returned Go and passed skills generation,
  proving the short-name issue. Its first attempt later hit the old project-name
  gate; that separately discovered gate is fixed in this final build.
- Final frozen worker passed DOCX export (0.714 s), HTML export (0.025 s) and
  bundled-asset verification (4.330 s), with only Windows directories in PATH.
- Real frozen-worker AWS recovery **completed** after more RAM became available.
  It restored completed sections and made seven remaining model calls: 120.275 s
  wall time, 2.131 GiB peak GUI/worker/model RSS and zero errors. This is a cached
  recovery, NOT a cold full-generation benchmark. Go was retained. Editing took
  1.4 ms; preview/autosave 6.2 ms; maximum sampled event-loop gap 103.9 ms.
- Final output: 1,793 words, 102 paragraphs, three roles, two projects and 37
  unique responsibility bullets. Identity/contact and four education rows were
  preserved. Employment/project date checks and edited DOCX/HTML exports passed.
- On the AWS JD's 45 extracted terms, mechanical keyword presence was 100%,
  combined narrative evidence 71.1% and project-only evidence 40.0%. These are
  heuristic text measures, not technical/ATS scores; some extracted phrases are
  noisy. Remaining narrative gaps are visible in the report; this parser fix
  does not claim comprehensive JD skill evidence or improved content scoring.
- The installer was built before recovery finished; its embedded test report
  records that test as pending. This external report contains the final result.
- Windows x64 app and installer rebuilt as 0.3.2. Saved data and previous
  versioned installers are preserved. Close the app before installing.
- No new clean-Windows/8-GB qualification is claimed. The 5m 07s real-model timing
  below is the earlier 0.3.1 Azure-JD test, not a measurement for this AWS JD.

## Changed files

`desktop/generation.py`, `desktop/test_generation.py`, `desktop/installer.nsi`,
`desktop/README.md`, `desktop/TEST_RESULTS.md`.

---

# Bounded generation update 0.3.1 - 15 October 2026

## Fixes for slow evidence checks and project-design failures

- Removed all post-generation per-skill model calls. Evidence checking now runs
  locally; unmatched skills remain visible in the HTML report. Required skills
  are assigned during the original experience/project writing calls.
- Kept the same complete fabricated workflow: three employment roles, two
  detailed projects, eight technical and three functional bullets per project,
  categorized skills, summary and certifications. No source-only fallback.
- Initial generation uses 19 calls; at most two optional duplicate-replacement
  calls and three validation retries across the whole resume (at most 24
  generation submissions, before any transport retry). Each section gets at
  most one validation retry. No per-skill evidence retry loop remains.
- Project-design punctuation and evaluation wording are normalized locally.
  Missing the exact dataset/held-out wording shown in the screenshot no longer
  causes a failed resume. Nonempty complete fields are retained. An evaluation
  sentence without a test-set reference gets a fictional held-out test-case
  method with task-success and latency measures; no percentage is added.
- Inconsistent percentage baselines and unresolved repeated bullets become
  HTML review notes rather than discarding an otherwise complete resume.
  Malformed/missing required fields and known invalid technical claims still
  fail if their small retry budget is exhausted; model failures are not hidden.
- Existing date removal, identity/education preservation, memory safeguards,
  offline/private model runtime, editing, autosave and exports remain.

## Verification

- **38 regression tests passed**, including the screenshot's evaluation wording,
  punctuation normalization, global retry budget, absence of evidence calls,
  duplicate repair bounds, complete fictional structure, and existing checks.
- Final frozen worker: DOCX export, HTML export and checksums of all bundled
  assets passed with only Windows directories in PATH. Export smoke wall times
  were 3.062 s (first DOCX) and 0.039 s (HTML); asset verification was 4.874 s.
- Fresh final frozen-worker test on the same eight-page candidate PDF and
  69-word Azure JD, no cached sections: **307.382 seconds (5m 07s), 20 model
  calls, one validation retry, 2.168 GiB peak GUI/worker/model RSS, zero errors**.
  The earlier 0.3.0 result was 713.736 seconds / 63 calls: about 57% lower elapsed
  time in these observed runs. User apps were closed and installer compression
  overlapped the beginning of this run; this is not a controlled speed guarantee.
- Editing handler 1.8 ms; preview/autosave 14.1 ms; maximum sampled Qt event-loop
  gap 104 ms. Active cancellation acknowledged in 11.7 ms; none of the four
  owned processes remained after 500 ms. Edited DOCX/HTML exports passed.
- All employment/project date checks, four education rows and identity/contact
  preservation passed. Output: 2,154 words, 101 paragraphs, 37 unique bullets.
- The same 34-term rubric: keywords 100%, combined narrative evidence 82.4%,
  project-only evidence 73.5%. The 0.3.0 tail repairs achieved 94.1% / 91.2%;
  removing them trades automatic evidence additions for much shorter waits.
  Combined gaps: AI security/governance, API integration, Azure AI Agent Service,
  LLMOps, Python and vector databases. Project-only gaps additionally include
  agentic AI, LangChain and RAG. These are text checks, not ATS/semantic scores.
  No coverage gain is claimed for this latency fix; gaps remain visible.
- The screenshot's missing evaluation wording no longer aborts the resume.
  Frozen HTML review notes were also checked for correct escaping.
- Installer was rebuilt; its install/uninstall logic is unchanged except the
  displayed version. The previous isolated lifecycle results below are 0.3.0
  results, not a new 0.3.1 installation test on a clean machine.

The installer was packaged before the fresh benchmark finished; its embedded
report records that test as pending. This external report contains final results.

## Files changed in 0.3.1

`desktop/generation.py`, `desktop/draft.py`, `desktop/test_generation.py`,
`desktop/installer.nsi`, `desktop/README.md`, `desktop/TEST_RESULTS.md`.

The 8 GB reference laptop, physically disconnected clean Windows test and
broader technical review gates below still apply. Coverage can be lower than
0.3.0 because missing skills are reported instead of repeatedly regenerated.

---

# Date-free quality update 0.3.0 - 15 October 2026

## Implemented

Employment and project calendar dates are removed during generation, restored
preview and both exports, including manually entered dates. Education years,
technical product versions, numeric dataset counts and experience-length claims
remain. Employers and clients stay named; no confidential label is added.
Full fictional experience, skills, certifications and metrics remain permitted.
The simple interface is retained.

Projects have explicit business problem, architecture, data flow, evaluation,
deployment, security and outcome fields. Scoped technical responsibilities and
stakeholder/governance/handover responsibilities replace repeated generic blocks.
Validation checks completeness, near repeats within technical blocks, exact
cross-section duplicates, known Key Vault/API hosting errors and conflicting
explicit percentage baselines. Targeted evidence repairs are bounded; unresolved
gaps remain visible. These checks are not exhaustive technical verification.
Old generation caches are retained but no longer reused by the new prompts.

## Fresh packaged-worker measurement

Windows 11 x64 development laptop, build 26200, nominal 16 GB RAM and 10 physical
CPU cores; inference uses four CPU threads, no GPU, one 4,096-token slot and
768 output tokens per call. Source: the candidate's **eight-page text PDF**, and
the saved **69-word Azure GenAI Lead JD**. New isolated profile: no AI section
cache. A headless Qt GUI harness used the final frozen worker. This is not a
benchmark on the specified 8 GB/four-core reference laptop.

| Measurement | Result |
| --- | --- |
| Full generation wall time | 713.736 seconds |
| Actual model calls, including repairs | 63 |
| Peak GUI + worker + child-model RSS | 2.264 GiB |
| Editor change handler | 1.7 ms |
| Preview refresh and autosave | 14.1 ms |
| Largest sampled Qt event-loop gap | 119.1 ms |
| Active-request cancellation acknowledgement | 18.2 ms |
| Owned processes remaining 500 ms after cancellation | 0 |
| Generation errors | 0 |

An earlier packaged attempt hit the 4 GiB guard. Inspection of the bundled
runtime's own help revealed its auxiliary prompt RAM cache defaults to 8 GiB.
The final runtime uses `--cache-ram 0`, with prompt batch 256 and microbatch 64;
the active 4,096-token context is retained. The memory/startup guards remain.
Other user applications were left alone. Timings describe this development
laptop under its existing workload, not guaranteed performance on every laptop.

## Same-JD comparison

The earlier v0.2 saved candidate/JD document and fresh v0.3 document were scored
with the same 34-term local rubric. Keyword presence is
separate from action/mechanism passages of at least twelve words. Tools-only
metadata does not count as narrative evidence. No overall ATS or semantic
technical-quality percentage is inferred.

| Mechanical measure | Earlier | Fresh |
| --- | --- | --- |
| Required-skill keyword presence | 100.0% | 100.0% |
| Experience or project narrative evidence | 85.3% | 94.1% |
| Project-only narrative evidence | 76.5% | 91.2% |

Remaining combined narrative gaps: **llmops, vector databases**.
Remaining project-only gaps: **cost optimization, llmops, vector databases**.
The report quotes matched passages for inspection. Invented metrics are
fictional claims, not independently verified business outcomes.

Fresh output: 2464 words,
109 paragraphs, three roles, two projects,
45 distinct responsibility bullets. The supplied previous
`resume.docx` has 2261 words and
251 paragraphs; `sample-resume.docx`
has 1339 words and
91 paragraphs. Counts describe
organization and detail, not an independent quality score. Manual review still
found overlapping security-focused project domains and imprecise retrieval /
prompt-injection explanations. These remain qualitative weaknesses despite the
higher text-evidence coverage; the sample is not technically certified. All seven design
labels occur in both projects with bold labels; subheadings keep with following
paragraphs. Candidate name/contact and four education rows are preserved.
Employment/project calendar checks and exact-duplicate checks passed.

## Verification

- **35 regression checks passed**: generation structure and repairs, date
  sanitation, education preservation, skill/report behavior, editing/undo,
  autosave/recovery, current-edit exports, missing/corrupt assets, startup
  memory/context limits, bounded queues, private model ownership and idle unload.
  PyMuPDF emitted only existing SWIG deprecation warnings.
- Fresh real-model resume generated with the final frozen worker. Model is CPU-only,
  bound to 127.0.0.1 with a session key; no other app's model is reused or stopped.
- Final frozen-worker cancellation left no owned child processes after 500 ms.
- Final frozen-worker DOCX and HTML exports contain a manual edit marker, remove
  a manually inserted employment date range, and include the HTML evidence table.
- Isolated installer namespace: install 40.77 seconds,
  upgrade 19.15 seconds, uninstall 1.12
  seconds. First launch, restart, worker exports, saved-data preservation across
  upgrade/uninstall passed. Test PATH contained Windows directories only.
  The real existing installation registration was checked and preserved.
- Offline flags are enabled and all model/runtime/embedding assets are bundled.
  This host has development tools and was not physically disconnected.

The final installer is unsigned. Close the installed desktop application and run
`dist/ResumeOptimizerDesktopSetup.exe` to upgrade; user data remains in
`%LOCALAPPDATA%/ResumeOptimizerDesktop`. Previous installers are preserved.

## Changed files for this update

- `desktop/quality.py`: date sanitization, required names, evidence and HTML table.
- `desktop/generation.py`: date-free structured generation and bounded repairs.
- `desktop/draft.py`: current-edit exports and design labels/report recalculation.
- `desktop/storage.py`, `desktop/app.py`: sanitize restored drafts and previews.
- `desktop/runtime.py`: bounded prompt batches, disabled auxiliary RAM cache,
  varied validation-retry sampling seeds.
- `desktop/prepare_assets.py`: preserve identical runtime DLLs during rebuilds.
- `desktop/installer.nsi`: version 0.3.0 and isolated QA installer identifiers.
- `desktop/gui_smoke.py`, `desktop/install_smoke.py`: packaged-worker/candidate
  benchmarks and safe isolated installer lifecycle checks.
- `desktop/test_generation.py`, `desktop/test_desktop.py`: regression coverage.
- `desktop/README.md`, `desktop/TEST_RESULTS.md`: usage and measured results.

Generated artifacts are under `dist/desktop-v3-cachefix`,
`dist/ResumeOptimizerDesktopSetup.exe` and `dist/examples-v3`. Build-only test
helpers/JSON outputs live under ignored `build/`.

## Remaining release gates

- Clean Windows 11 x64 without development tools; physically disconnect before
  installation, first launch, generation and exports.
- Repeat on the actual 8 GB RAM/four-core/SSD reference laptop. The memory result
  above does not qualify that hardware or guarantee editor latency under all load.
- Broader qualitative review of model output; heuristic evidence coverage does
  not prove all generated architecture, numeric claims or terminology correct.
- Complete corresponding source distribution for copyleft components before
  public redistribution, as documented in `desktop/THIRD_PARTY.md`.

---

# Historical results (0.2 and earlier)

# Complete AI generation update - 14 October 2026

Version 0.2.0 replaces the template draft with complete fictional AI generation
and simplifies the interface. The historical measurements below describe
version 0.1.0 and **are not timings for the new full-generation workflow**.

## Current verification

- 23 regression checks pass, including complete-generation structure with
  simulated model responses, bounded repairs, education-table preservation,
  simplified GUI, editing/undo, and DOCX/HTML from current edits.
- Source PDF identity/contact extraction and four education rows checked on the
  uploaded candidate resume. Expected and previous output documents compared.
- Real CPU-model generation using the candidate PDF and saved Gen AI Lead JD
  produced 1,868 words, 81 paragraphs, three roles, and two projects with eight
  technical and three functional responsibilities each. The previous output had
  251 paragraphs and the reference has 91. Counts describe structure, not an
  independent quality score. Four education rows and contact details are preserved.
- Successful candidate retry: 122.774 seconds with some cached sections, peak
  worker/model RSS 2.444 GiB. A later retry took 10.721 seconds with all sections
  cached except certification selection, peak 2.048 GiB. Neither is a cold full
  generation timing. Earlier real runs exposed duplicate responsibilities,
  response count errors and chronology problems; those led to automatic repairs,
  constrained JSON arrays, skill normalization and validated-section caching.
- Initial low-memory launches safely refused model startup until RAM became
  available. Known tool/date and compute-host mistakes are checked or repaired;
  this is not an exhaustive validator of every possible technical claim.
- Certification possession remains fictional; recognizable published titles
  replace generic invented certification names.
- UI-only integration uses simulated responses; it does not establish model
  speed or output quality. Installation and artifact results are appended below.

### Fresh full-generation GUI benchmark

Windows 11 x64 development laptop, approximately 16 GB RAM, 10 physical CPU
cores; CPU inference capped at four threads, no GPU. Original API/n8n copy
remained running. This was a fresh test profile without cached AI sections.

| Check | Result |
| --- | --- |
| Three-page PDF and 2,000-word JD | Complete resume in 243.925 seconds |
| Model requests | 15, no validation repairs needed |
| GUI + worker + model peak RSS | 2.327 GiB |
| Editor change handler | 1.0 ms |
| Preview and autosave | 6.5 ms |
| Maximum Qt event-loop gap | 69.1 ms |
| Cancellation acknowledgement after completion | 14.3 ms |
| Cancellation during an active model request | 12.5 ms; no owned processes remained after 500 ms |
| Errors | None |

The JD fixture repeats Python/FastAPI/Docker requirements across numbered
modules. These measurements are not a speed guarantee for more complex JDs.
The specified 8 GB reference laptop and physically disconnected clean Windows
installation remain release gates. The local installer uses bundled assets and
was checked with PATH containing only Windows system directories.

### Final installer checks

- Version 0.2.0 installer: 1,402,648,855 bytes, including the offline model.
- SHA256: `0B6BB8256799B768F4FF6F2DE636AB49A40ACD987A17BF59188A41A1BAC825A9`.
- Final installation: 35.56 seconds; upgrade: 18.27 seconds; uninstall: 1.12 seconds.
- First launch, installed worker DOCX/HTML exports, restart and saved-data
  preservation passed with only Windows system directories in PATH.
- The final frozen worker loaded its bundled model and completed the candidate
  resume workflow using validated cached AI sections in 4.981 seconds. This is a
  cached retry measurement, not a fresh generation timing.
- Original API/n8n copy remained running. No public model port was opened.
- Clean disconnected Windows and an actual 8 GB reference laptop are still untested.

### Changed files in this update

- `desktop/generation.py`: complete generation, structured records, prompt budgets,
  constrained response lists, chronology checks, duplicate repair and local cache.
- `desktop/app.py`: simple input/result views, hidden editing controls, readable preview.
- `desktop/draft.py`: report extraction excludes recruiter scheduling/pay metadata
  and standalone titles; experience ranges are normalized while retaining the original JD.
- `desktop/worker.py`, `desktop/runtime.py`, `desktop/controller.py`: generation
  dispatch, constrained model responses and error messages.
- `desktop/build.ps1`, `desktop/installer.nsi`: fresh bundles and version 0.2.0.
- `desktop/test_generation.py`, `desktop/test_desktop.py`, `desktop/smoke.py`,
  `desktop/gui_smoke.py`, `desktop/install_smoke.py`: regression and lifecycle checks.
- `desktop/README.md`, `desktop/TEST_RESULTS.md`: usage and measured results.

### Technical references

Historical checks use announcements for
[MCP](https://www.anthropic.com/news/model-context-protocol),
[LangGraph](https://www.langchain.com/blog/langgraph), and
[Azure AI Foundry](https://azure.microsoft.com/en-us/blog/the-next-wave-of-azure-innovation-azure-ai-foundry-intelligent-data-and-more/).
Constrained response formats follow the
[llama.cpp server documentation](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).
Certification title references include
[Microsoft](https://learn.microsoft.com/en-us/credentials/certifications/devops-engineer/),
[AWS](https://aws.amazon.com/certification/certified-machine-learning-engineer-associate/), and
[CNCF](https://www.cncf.io/training/certification/).

## Previous version measurements (historical)

# Desktop test results — 14 October 2026

Build: Windows x64 development preview. The machine was Windows 11 build
26200, Intel Core i5-13450HX, 10 physical cores, approximately 16 GB RAM.
GPU acceleration was not used. This is not the specified 8 GB / four-core
reference machine.

| Check | Result |
| --- | --- |
| Desktop regression tests | 17 passed |
| ONNX vs PyTorch classification agreement | 97.43%, 1,013 classifications across 50 repository gold fixtures |
| Three-page text PDF and 2,000-word JD, GUI integration | Draft in 5.688 seconds |
| Editor change handler | 0.1 ms |
| Preview refresh plus autosave | 8.7 ms |
| Maximum Qt event-loop gap in draft integration test | 77 ms |
| GUI and worker memory during fast-draft integration | 299 MiB peak |
| Native CPU demo summary polishing (earlier successful run) | 17.741 seconds, including model startup/checks |
| GUI + worker + model peak in successful polishing integration | Approximately 2.26 GiB |
| DOCX and HTML from edited content | Passed, both source and packaged worker |
| GUI first launch from installed bundle | Passed with PATH limited to Windows system directories |
| Local installer installation / upgrade | 35.56 seconds / 23.25 seconds |
| Restore edited draft after upgrade | Passed |
| Uninstall | 1.13 seconds; application payload removed, user-data markers preserved |
| Missing/corrupt assets, scanned PDF, insufficient RAM | Explicit errors tested |
| Queue and cancellation | One active/one waiting; rejection and owned-process cleanup tested |
| Cancellation acknowledgement during polishing integration | 15.8 ms |
| Fictional/demo mode | Default and preserved; invented claims accepted without source-only guard |
| Original local copy coexistence | Existing API/n8n and original model remained running during desktop checks |

Measurements use different test samples and runs; they are not universal
latency guarantees. The model polishing number is for one short summary,
not a full resume. ONNX comparison reconstructs identical source text from
gold facts for both embedders and measures agreement, not overall accuracy.

Worker benchmarks set Hugging Face/Transformers offline flags, load all
assets from local files, and use loopback for model calls. Installed GUI/worker
checks did not rely on Python, Docker or n8n being in PATH. However, the host
itself contains development tools and was not physically disconnected.

Later tests encountered less than 2.3 GB free RAM because other applications
and the original model were running. The desktop correctly deferred AI
polishing and kept the fast draft/editor usable.

## Outstanding release qualification

- Clean Windows 11 x64 machine or VM with no development tools installed.
- Physically disconnected installation, first launch, polishing and exports.
- Repeat performance and memory measurements on the specified 8 GB /
  four-physical-core CPU / SSD reference laptop.
- Review polished outputs on representative real resumes/JDs, including long
  sections, metadata preservation and fictional/demo content.
- Prepare complete corresponding source distribution for copyleft components
  before public redistribution, as described in THIRD_PARTY.md.

Detailed local outputs are in build/desktop-embedding-validation.json,
build/desktop-gui-smoke.json and build/desktop-installer-smoke.json.
