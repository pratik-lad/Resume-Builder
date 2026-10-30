# Project Edition 1.5.0 - model upgrade verification

## Selected model

- Qwen3-4B-Instruct-2507, Q4_K_M, from `unsloth/Qwen3-4B-Instruct-2507-GGUF`.
- Exact revision `a06e946bb6b655725eafa393f4a9745d460374c9`.
- 2,497,281,120 bytes (2.50 GB decimal / 2.33 GiB); SHA-256 `3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597`.
- Apache 2.0; base-model licence pinned to revision `cdbee75f17c01a7cc42f958dc650907174af0554`.
- One 4,096-token CPU slot, at most 768 output tokens, four threads on this host,
  private loopback session key, no weight repacking. No model training/fine-tuning.

Official sources: [Qwen model card](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507),
[GGUF quantizer](https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF).

## Controlled comparison before integration

Host: Windows 11 x64, Intel i5-13450HX, approximately 16 GB RAM. CPU inference;
other user applications stayed running. This is not the 8 GB reference laptop.
Both downloads were checked against the quantizer's published SHA-256 and size.
The same recorded Salesforce and Java project contexts and seed were used.

| Candidate | GGUF bytes | Peak sampled harness/model RSS | Salesforce summary test | Java summary test |
| --- | ---: | ---: | ---: | ---: |
| Qwen3.5-4B Q4_K_M | 2,740,937,888 | 3,359,567,872 / 3.13 GiB | 162.306 s | 126.343 s |
| Qwen3-4B-Instruct-2507 Q4_K_M | 2,497,281,120 | 3,287,359,488 / 3.06 GiB | 149.436 s | 129.067 s |

These are summary-only comparisons using the previous validators, four logical
submissions per fixture, not complete-resume timings. Both originally fell back;
inspection found discarded useful text, punctuation differences, strict word
counts and prose incorrectly detected as tool names. The new integration corrects
those validation issues without claiming that larger weights alone solve quality.
Qwen3 Instruct was selected for its smaller footprint, non-thinking text focus
and closer professional-profile style in the recorded responses. This is a local
qualitative selection, not proof of superior output across every JD.

With default CPU weight repacking, both candidate startup tests crossed 4 GiB and
were stopped. Disabling repacking kept the controlled runs within the target.
Download size is not RAM usage. The running-memory safeguard remains active;
no 2.3 GB free-RAM gate was restored. GPU and Mac hosting are not enabled here.

## Packaging and compatibility

Model filenames come from the verified asset manifest. Cache identity includes
model filename/checksum, and new document metadata records the model. Previous
saved drafts are not rewritten. Preparation leaves older GGUF files on disk but
only manifest-listed assets enter the frozen application. Full fictional
professional generation, three employers, date-free output and local credential
selection remain enabled.

The larger offline installer uses the free NSISBI 3.12.3 compiler; ordinary NSIS
has a 2 GiB EXE limit. The compiler archive is pinned in installer-toolchain.json.
[Official large-installer support](https://sourceforge.net/projects/nsisbi/files/nsisbi3.12.3/).
The previous complete 1.4.0 / 2B installer is retained at
`dist/ResumeOptimizerProjectsSetup-1.4.0-2B.exe` for rollback.

## Release qualification

Full packaged-generation measurements and final artifact checks are published
beside this source after packaging. Clean disconnected Windows installation,
upgrade/uninstall and an actual 8 GB reference-laptop benchmark remain release
gates when that hardware is unavailable. No external ATS percentage is claimed.

## Integration findings before final qualification

The first packaged full-stack trial with legacy low-temperature sampling failed
at project 1 overview: repeated sentences exhausted 768 tokens twice. Peak RSS
was 3,379,200,000 bytes (3.15 GiB). That trial is not a successful release test.
The integration uses model-specific sampling and a separate business-only
overview context. Character-cap experiments caused padding/input leakage in
this model and were rejected; structural schemas, prompts, validators and the
768-token response limit remain. These changes are verified before the final
packaged run. This failed intermediate build is retained in local build logs.

## Model-specific decoding and section scope

The old 0.35 temperature produced a repeated overview that exhausted two calls.
The selected profile uses temperature 0.7, top-p 0.8, top-k 20, min-p 0,
presence penalty 1.0 and repeat penalty 1.1. The first four values follow the
[model card's sampling guidance](https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507#best-practices);
the two modest anti-repetition values are local tuning, not a guarantee against
all repeated content. Settings are pinned with the model and included in cache
identity and document provenance.

A detailed implementation acceptance list also encouraged whole-project prose
inside the overview. The overview now receives only target role, project,
business problem and deliverable. Deep capability requirements remain in the
project responsibility calls. The system explicitly distinguishes the current
`task` instruction from reference context. Full fictional content stays enabled.

## Final packaged verification

All results below use the final **1.5.0** bundle, not the failed intermediate
build. Exact acceptance input: `sample-resume.pdf` and the repository's
152-word Senior Full Stack Developer JD fixture. It is the same supplied input
and JD, with a fresh generation identity and no reused generation cache.

| Check | Observed result |
| --- | --- |
| Source regression suite | 143 passed; five existing PyMuPDF/SWIG warnings; 140.47 s |
| Fresh full generation | 719.281 s (11 min 59 s), 23 logical model submissions, no completion errors |
| Sampled peak GUI + worker + model RSS | 3,436,244,992 bytes / 3.20 GiB |
| Repairs | Two project quality calls and one summary validation retry, within the 27-submission ceiling |
| Summary | Six bullets: 43, 34, 32, 37, 34, 30 words; first three model-written, last three structured fallback |
| Experience | 8+ overall years, including 5+ full-stack years; no overlapping totals added |
| Certifications | Three relevant AWS credentials selected from the offline catalogue |
| Editor handler / preview + autosave | 1.1 ms / 14.1 ms |
| Maximum sampled GUI event-loop gap | 97.2 ms in this run; not a guarantee for other laptops |
| Active cancellation | 17.3 ms acknowledgement; zero owned processes left at the 750 ms check |
| Native bundled startup + self-close | 1.655 s with Python removed from PATH |
| Installed startup + self-close | 2.270 s, isolated installation, Python removed from PATH |
| Isolated installation / upgrade | 58.455 s / 26.556 s; saved data preserved |
| Isolated uninstall | 1.282 s; saved data preserved; real application registry and draft unchanged |
| Installed assets | 127 files verified, including exact SHA-256/size of the >2 GiB GGUF |

CPU observations cover approximately 680.64 seconds beginning after generation
launch, sampled about once per second. Mean tree CPU was 400.27% and peak 415.62%
when 100% means one logical CPU; the peak is 25.98% of the host's 16 logical CPUs.
The model used four inference threads. These observations are not a separate
8 GB reference-laptop or formal cold/warm-start benchmark.

The isolated installer test compiles the same final bundle and scripts with a
unique test app/registry/shortcut identity, then installs, upgrades and uninstalls
only a newly created test directory. No existing user installation was removed.
The actual larger model was extracted and verified after installation. This is
not a clean Windows machine without preinstalled system components.

DOCX/HTML exports preserve the current edited text and recalculate edited-report
coverage. Summary bullet count, three distinct projects/employers, six bullets
per project, target-role metadata, Confidential client masking, bold skill groups,
certifications and absence of generated calendar dates were checked. A deliberate
4+ years edit remains in both exports and changes the experience report. Undo/redo,
autosave recovery, missing/corrupt assets, low-free-RAM startup behavior, queueing,
context overflow and edition separation are covered by the regression suite.

Seven Salesforce, full-stack, Java, Databricks, AWS, Azure GenAI and QA fixture
contracts use a stub runtime. The real fresh full 4B run here is full-stack;
summary-only comparisons and seed tests do not establish real-model quality
across every fixture. Internet was available on the host; physically disconnected
clean-Windows and actual 8 GB reference-laptop tests remain release gates. Mac,
Metal/GPU hosting, tunnel access and automatic server startup remain deferred.

## Quality review and remaining gaps

- The first summary half is generated directly by the model. The second half
  used the bounded fallback because it claimed Agile implementation not found
  in the generated project passages. Completed project content was retained.
- Local mandatory keyword presence: 11/11; preferred: 3/3. Mandatory evidence
  checks: 10 supported, 8 partial, 3 missing; preferred evidence: 3 supported.
  Checks include overlapping named capabilities and raw JD clauses; these are
  not 21 independent requirements or an external ATS score.
- Named Copilot/Cursor/ChatGPT development workflow and explicit Agile
  collaboration still need stronger project evidence. The report also retains
  three metric/workload/baseline/result warnings after bounded repair.
- Some literal gap detection is stricter than a human review: escaped phrases
  such as REST API/API integration can be flagged despite related FastAPI/REST
  passages. Do not interpret these counts as an external ATS percentage.
- Projects are distinct: Smart Code Assistant Platform, Real-time Analytics
  Dashboard and Dynamic Workflow Engine. Role metadata and business purposes
  differ; summaries/certifications remain professional fictional claims.
- No 95% external ATS result or universal speed/quality improvement is promised.

## Delivered artifacts

- Installer: `dist/ResumeOptimizerProjectsSetup.exe`, 2,620,449,668 bytes.
- Installer SHA-256: `412569442cee6bf3c8c588a9e15b5a60f9ef95bc5966294398239d703bf99538`.
- Rollback: `dist/ResumeOptimizerProjectsSetup-1.4.0-2B.exe`; verified SHA-256
  `6a10b8dfedc44d69f55fe5da86c95d9bc7c9ddd42b52ec9c5d30448e0ff431c9`.
- Fresh sample: `build/model-candidates/FullStack_4B_sample.docx`.
- HTML report: `build/model-candidates/FullStack_4B_sample.html`.
- Exact bundle and model pins: `build/project-latest.json` and `desktop/assets.json`.
- Detailed logs/measurements: `build/model-candidates/` (local, ignored by Git).

## Files touched for this model upgrade

- Model/runtime: `desktop/assets.json`, `desktop/runtime.py`, `desktop/prepare_assets.py`.
- Generation/validation/cache: `desktop/generation.py`, `desktop/project_generation.py`, `desktop/project_profile.py`.
- Packaging: `desktop/desktop.spec`, `desktop/installer.nsi`, `desktop/project_installer.nsi`, `desktop/build_projects.ps1`, `desktop/build.ps1`, new `desktop/installer-toolchain.json`.
- Regression checks: `desktop/test_desktop.py`, `desktop/test_project_profile.py`, `desktop/test_general_quality.py`.
- Documentation: `README.md`, `desktop/README.md`, `desktop/PROJECT_EDITION.md`, `desktop/THIRD_PARTY.md`, `docs/DESKTOP_INSTALLATION.md`, `docs/DESKTOP_REQUIREMENTS.md`, `docs/DESKTOP_TECHNICAL_OVERVIEW.md`, this report.

Earlier Phase 1 work in other files was preserved. No existing source files,
models, user drafts or previous installers were deleted. Full fictional generation
remains enabled; edited text remains export authority. The removed 2.3 GB
free-RAM startup gate stays removed, and the running 4 GiB safeguard remains.

## User steps and checklist

Close Project Edition, run the new installer, then generate a fresh resume.
Existing saved drafts are deliberately not regenerated automatically.

```powershell
Set-Location 'C:\path\to\Resume-Builder'
& '.\dist\ResumeOptimizerProjectsSetup.exe'
```

Check one generation, six summary bullets, correct separate experience totals,
relevant certifications, three distinct projects, edits/undo/redo, restart/autosave
recovery, cancellation, and both edited DOCX/HTML exports. Review remaining report
gaps manually before approving Phase 2. There is no hosting account or API bill.
