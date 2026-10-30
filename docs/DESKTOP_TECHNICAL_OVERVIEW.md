# Project Edition 1.6.0 - reference layout and GPU generation

The current engine preserves full fictional professional generation. It extracts a complete JD requirement ledger, assigns ownership across three distinct projects, writes five technical and two functional responsibilities per project, and writes six summary bullets after the career is complete. Identity and education qualifications are parsed from the supplied resume. Calendar dates are removed; overall and specialty experience durations remain separate.

The base workflow uses 11 model calls: planning (1), two calls per project (6), skills (2), summary (2). Long requirement ledgers are batched using the rendered model token count. Three shared malformed-response retries and two targeted quality repairs remain bounded by 27 actual generation requests, including HTTP retries. Keyword presence and mandatory/preferred implementation passages are reported separately, with links to edited project bullets. These local checks are not an external ATS score.

The model selection and sampling are pinned in `desktop/assets.json`; GGUF checksums also pin the embedded chat template. Each call has a 4,096-token slot and at most 768 output tokens. Windows automatically tries the bundled CUDA runtime on supported NVIDIA hardware, a partial layer allocation, then the CPU runtime. GPU layers are offloaded, not partitioned into an isolated memory slice. The CUDA runtime is built from pinned llama.cpp b11316 source, commit `2232bc8b5f8cd91493a2c251b077c4d45cf2e832`, using CUDA 13.3.1 with an RTX 30-series baseline. The CPU fallback remains available on other supported Windows x64 laptops. Installed users do not need Python or a CUDA toolkit.

The PySide6 interface keeps parsing/inference/exports in its owned worker processes. The model binds to loopback with a random session key. One generation runs while one can wait; cancellation closes only owned processes. The removed 2.3 GB startup gate stays removed. The running-memory monitor and idle unloading remain enabled. Windows RSS and device-wide GPU memory are measured separately.

Preview, DOCX and HTML use the same edited section text. The reference layout has blue headings, centered identity, skills/education tables, compact project metadata and separate technical/functional bullets. DOCX rows cannot split, metadata stays together, and heading paragraphs remain with their following content. Saved drafts are not regenerated on upgrade. Reports are recalculated after edits.

Verification and model-comparison results are in [the release report](../desktop/QUALITY_REFERENCE_RESULTS.md). Mac browser hosting, Metal qualification, automatic startup and free tunneling remain Phase 2 after quality approval.

---

## Historical implementation notes (1.5.0 and earlier)

# Project Edition 1.5.0 - 4B instruction model

The selected offline model is **Qwen3-4B-Instruct-2507 Q4_K_M**, a 2.50 GB GGUF.
It uses the existing CPU llama.cpp runtime with one 4,096-token slot, at most
768 output tokens, and weight repacking disabled to avoid duplicate buffers.
Model selection, checksums, decoding settings and licences are manifest-driven.
The overview receives a short business brief rather than implementation acceptance
instructions. Decoding uses temperature 0.7, top-p 0.8, top-k 20, min-p 0, presence
penalty 1.0 and repeat penalty 1.1, tested to reduce repeated-output loops. Only the selected
weights are packaged; the previous 2B weights and installer are retained locally.

Summary generation remains project-led and uses six complete bullets. JSON schema
constrains the agreed role/experience opening. Local validation handles punctuation
and known technology aliases, with word-target deviations reported rather than
repeatedly discarding substantive sentences. Missing experience, very short or
long bullets, invented summary-only tools, repetition and metric leakage remain
reviewed. The model checksum is part of cache identity and new documents record
which model generated them. Full fictional professional generation is preserved.

Use **NSISBI 3.12.3** to build the single offline EXE above standard NSIS's 2 GiB
limit. The pinned toolchain is in `desktop/installer-toolchain.json`. Saved data,
the simple UI, the removed free-RAM startup gate and the 4 GiB running-memory
safeguard are preserved. Mac hosting/GPU/tunneling remain deferred.
See [model upgrade results](../desktop/MODEL_UPGRADE_RESULTS.md) for measurements and gates.

---

## Earlier version notes

# Version 1.4.0 ? general resume quality

Phase 1 now uses one versioned JD brief for role, overall/specialty experience,
mandatory/preferred requirements, technology and certification selection.
Project ownership follows requirement IDs and the planned business contribution;
it no longer uses a round-robin requirement split or fixed full-stack stack recipe.
Unfamiliar implementation requirements are retained for review.

The summary is written after repaired projects in two bounded calls, each asking
for three complete grammatical bullets. The opening targets 40?55 words; the
remaining bullets target 25?40 words. After bounded validation failure, a local
project-grounded fallback preserves six bullets and records its use in the report.
Skills retain bold domain-specific categories, tools and implementation practices.

Certifications are selected locally from a bundled catalogue of recognised titles,
source links, aliases and status. The normal target is three relevant credentials
(two to four where available), with required titles before preferred titles.
There is no optional model response that can silently return an empty certificate
list. Catalogue gaps and explicitly requested retired credentials are reported;
unrelated credentials are not added. Possession remains intentionally fictional.

Twenty normal model calls, up to two single-shot project repairs and three shared
validation retries fit within the unchanged hard ceiling of 27 submissions.
Edited section text remains export authority; reports recalculate edited evidence,
experience and credential presence. Prior saved drafts are not regenerated.

Full fictional generation and date-free new output are preserved. The 2.3 GB
startup gate stays removed, and the existing 4 GiB process-tree safeguard stays.
The CPU model, offline assets and simple interface are unchanged in this phase.
Mac hosting, GPU offloading and tunneling are deferred until quality approval.
See `desktop/GENERAL_QUALITY_RESULTS.md` for measured results and release gates.

---

## Historical documentation

# Version 1.3.0 full-stack quality update

Project Edition keeps overall and specialty experience separate, taking the higher explicit source/JD total. Full-stack planning assigns frontend/backend, requested GenAI, and production delivery ownership. HTML reports re-evaluate edited duration claims and implementation passages. The 2.3 GB startup gate was removed in 1.2.1; the 4 GiB runtime cap remains. Model/runtime and fully fictional generation are unchanged. See `desktop/FULL_STACK_RESULTS.md` for current results; older sections below describe historical releases.

# Offline Windows Resume Builder
## How Project Edition works

Technical overview | Updated 24 October 2026 | Project Edition 1.2.0 | Quality pipeline projects-quality-6

## Phase 1 changes in 1.2.0

- A fresh generation seed and cache identity are created for each Generate action.
- Planning assigns three contributions; each project renders its target role,
  contribution, overview, compact metadata and six implementation bullets.
- Up to two targeted project repairs run before the professional summary.
- The summary is written in two requests of three substantial bullets each,
  from the completed project implementations. It starts with the target role
  and numeric experience: the explicitly stated resume total, JD requirement,
  or 9+ years as fallback. Ranges use their lower bound; dates are not counted.
- Two bounded skills requests produce bold JD-specific categories containing
  both relevant technologies and implementation practices. Required technology
  names can be completed locally; that alone never counts as project evidence.
- Certification candidates are selected by JD platform/domain. The model may
  choose up to four relevant titles, with no mandatory fixed trio. Possession,
  experience, projects and metrics remain intentionally fictional.
- Schema-6 documents omit education dates as well as other body calendar dates,
  preserving qualifications and experience durations. Old drafts retain their
  versioned date behavior; edited sections remain export authority.
- The report separates mandatory/preferred keyword counts from supported,
  partial and missing capability evidence, with passages and review warnings.
- The normal maximum is 21 section calls + two project repair calls + three
  shared validation retries (26); the existing hard guard remains 27.

RAM checks, CPU inference, model/context settings, offline operation and the
simple interface are unchanged. Mac hosting and GPU acceleration are deferred
to Phase 2 after user acceptance. See [Phase 1 results](../desktop/PHASE1_RESULTS.md)
for current measurements. The architecture details below include historical
1.1.0 behavior and measurements; those timings do not describe the new workflow.

## 1. What the application does

Resume Optimizer Project Edition is a Windows desktop application that creates an editable resume from an uploaded resume and a pasted job description (JD). It runs the language model locally on the laptop's CPU. Its generation workflow is designed for offline use after the required runtime and model assets are installed.

The user chooses a text PDF or DOCX resume, pastes the JD, and selects Generate. The application shows progress and supports cancellation. The completed document can be edited, previewed, autosaved, and exported as DOCX or an HTML report.

Full fictional generation is enabled. The parser preserves the uploaded candidate's name, detected contact details, and identified education. The model generates professional content such as employers, experience, projects, skills, certifications, and outcomes. Those generated claims are fictional; the application does not verify employment or qualifications.

The current Project Edition format groups three employer/designation blocks under Relevant Project Experience, with one project per block. Each new project has a short overview, compact metadata, and six implementation bullets. Employer names remain visible. Project clients use Confidential client. Employment and project dates are removed; education details are retained.

## 2. System architecture

The application uses three cooperating components on the same computer:

| Component | Technology | Responsibility |
| --- | --- | --- |
| Desktop interface | Python and PySide6 / Qt | File selection, JD input, progress, editing, preview, undo/redo, and autosave scheduling |
| Background worker | Separate Python process, packaged as a worker EXE | Parsing, generation orchestration, validation, and document exports |
| Local inference server | llama.cpp llama-server.exe | Loads the GGUF model and performs CPU text generation |

The interface and worker exchange newline-delimited JSON messages through standard input and output. Messages carry a job ID, stage, status, and a result or error. The worker sends model requests over HTTP to its own loopback server using an OpenAI-compatible /v1/chat/completions endpoint.

Workflow: Resume + JD -> Local parsing -> Requirement classification -> Career/project plan -> Section generation -> Quality checks and bounded repairs -> Structured document -> Editing and preview -> DOCX / HTML export.

Cloud products such as Databricks, AWS, Genie, or Collibra mentioned in a generated project are resume content. The desktop app does not provision those services or require accounts for them.

The desktop workflow calls the reused Python modules directly. Docker, n8n, a cloud VM, and a separately hosted API are not required for this desktop path. Other deployment files in the repository belong to separate deployment arrangements.

## 3. Generation method

The method combines prompt decomposition, JSON-schema-constrained generation, local normalization, and rule-based review. It uses the bundled pretrained model for inference; this generation path does not train or fine-tune model weights.

### Step 1 - Parse the uploaded resume

PyMuPDF reads PDF text and supports recovery of education tables. python-docx reads DOCX paragraphs and tables. Existing segmentation code identifies the header and education sections. Identity and education are assembled outside model generation, reducing the chance that the model changes these fields.

The reader accepts PDF and DOCX inputs up to 25 MiB. It reports unreadable or scanned PDFs and missing identifiable education. OCR is outside this implementation. Extraction quality still depends on the input document's structure.

### Step 2 - Understand the JD

Local requirement-extraction code classifies JD statements into technologies, implementation capabilities, qualifications, and logistical details. Technology normalization, a technology catalog, and a small explicit alias map identify supported names. Preferred JD sections are tracked separately from required sections. Skill completion retains recognized technology names and supported short names, rather than copying requirement paragraphs into the skills section. Locations, notice-period information, proficiency adjectives, and fragments such as the GenAI engineering are excluded from named-technology coverage. Unknown technology names and semantic requirements still need review.

The full JD is available for planning and final reporting. Project-writing calls receive a narrower scope containing the assigned contribution, platform, and implementation requirements. This helps the small model focus on one project instead of repeating the entire engagement in each role.

### Step 3 - Plan three distinct contributions

The model proposes a headline and three fictional roles with employers, project titles, problems, contributions, stacks, and capability assignments. Local code provides stable role IDs, distinct-employer fallbacks, and purpose-based title fallbacks.

There is also a bundled Databricks profile for JDs involving Databricks, Genie, and Collibra. It assigns separate ownership to context serving, metadata/governance integration, and lakehouse engineering. Other JDs use the general planning and requirement-distribution path. This is a combination of generated planning and explicit rules, rather than universal semantic understanding of every technology.

### Step 4 - Generate small structured sections

The model writes the summary and skill categories, then generates each project's metadata, overview, internal design, and two groups of three responsibilities. Each group is returned as named JSON fields, giving the model a specific purpose for every bullet:

| Field | Intended content |
| --- | --- |
| data_flow | Sources, transformations, and destination |
| implementation | Core business or technical mechanism |
| integration | Interfaces, object mappings, and failure handling |
| security | Authentication, authorization, and credential handling |
| evaluation | One defined metric, workload or dataset, baseline, and final result |
| delivery | Deployment assets, rollback, documentation, and handover |

Internal design fields cover the problem, architecture, data flow, security, evaluation, deployment, and outcome. They guide the responsibilities without all being repeated as separate exported paragraphs. Before rendering, local normalization removes dates, applies the client label, and corrects selected naming mistakes. Schema constraints improve structure; they cannot guarantee factual technical correctness.

Requests use JSON schemas to constrain object fields, list sizes, team-size values, and allowed certification titles. Python validators check completeness, usable text, list entries, and selected technical constraints. The current implementation uses 19 base model calls before cache hits or retries: planning, summary, skills, five calls for each of three projects, and certifications.

### Step 5 - Review and repair

Local checks look for selected version conflicts, unexplained AWS/Azure mixtures, incorrect secrets-store usage, confusion between retrieval chunks and ingestion batches, weak percentage claims, arithmetic mismatches, inconsistent baseline/result metric names such as accuracy versus precision, and repeated or near-duplicate bullets.

The pipeline permits at most three malformed-response retries, with no more than one retry for an individual section. A separate shared budget allows at most two single-shot quality-repair calls, targeting different projects so both attempts are not repeatedly spent on one project. These calls have no nested validation retry. A proposed repair is rejected when it increases the local penalty for warnings and missing required evidence. Remaining issues are included in the report. The usual maximum is 24 model calls under these budgets, with a hard guard at 27 generation submissions. Bounded HTTP transport retries are a separate mechanism.

Successful section responses can be cached locally. Cache keys include the generation system prompt and request content; the Project Edition quality revision is part of that prompt. Changes to those inputs produce different keys. Saved responses are validated again before reuse.

## 4. Models and inference configuration

### Main text-generation model

| Setting | Current configuration |
| --- | --- |
| Model | Qwen3-4B-Instruct-2507 |
| Bundled file | Qwen3-4B-Instruct-2507-Q4_K_M.gguf |
| Model repository | unsloth/Qwen3-4B-Instruct-2507-GGUF |
| Pinned revision | a06e946bb6b655725eafa393f4a9745d460374c9 |
| Quantization | Q4_K_M |
| File size | 2,497,281,120 bytes, approximately 2.33 GiB |
| Inference runtime | llama.cpp Windows CPU x64, build b11316 |
| Context and slots | 4,096 tokens; one slot |
| Output budget | At most 768 tokens per call |
| CPU threads | max(1, min(4, physical CPU cores - 1)) |
| GPU offload | Disabled in the baseline runtime configuration |
| Reasoning mode | Disabled through the chat-template/request settings |

GGUF is the model format loaded by llama.cpp. Q4_K_M is a quantized weight representation that reduces the model file and memory requirements relative to higher-precision weights. The total application memory use also includes the inference cache, server, Python worker, interface, and document libraries; it is larger than the GGUF file alone.

Before submission, the worker asks llama.cpp to render the chat template and tokenize the request. It rejects a request if the rendered prompt plus the 768-token output allowance exceeds the 4,096-token context. JSON-generation requests use temperature 0.35 and an initial seed of 42; a validation retry uses seed 43. These settings improve repeatability but do not guarantee identical results on all runtime builds or hardware.

The manifest records the model's SHA-256 checksum as aaf42c8b7c3cab2bf3d69c355048d4a0ee9973d48f16c731c0520ee914699223. Asset checks compare installed files against the manifest before use.

### Bundled embedding model

The asset manifest also includes Xenova/bge-small-en-v1.5 as a quantized ONNX model, pinned to revision ea104dacec62c0de699686887e3f920caeb4f3e3. Its adapter uses ONNX Runtime on CPU with one intra-operation and one inter-operation thread, CLS pooling, normalized vectors, and a 512-token input limit.

This embedding adapter supports the older deterministic/source-matching path. The current Project Edition complete-generation function does not install or call it. Project Edition's displayed keyword and capability checks use local text rules. Bundling an embedding model therefore does not mean that every resume-generation request performs embedding inference or retrieval-augmented generation (RAG).

## 5. Technologies and tools

| Technology or tool | Use in the application |
| --- | --- |
| Python 3.11 | Application logic, orchestration, workers, parsing, and exports |
| PySide6 6.8.3 | Native Qt interface, signals, timers, text editing, and preview |
| llama.cpp b11316 | Local GGUF loading, chat templating, tokenization, and inference |
| HTTPX 0.28.1 | HTTP communication with the owned local model server |
| PyMuPDF 1.25.1 | PDF text and table extraction |
| python-docx 1.1.2 | DOCX parsing and Word-document construction |
| Python regex and difflib | Text normalization, technical patterns, and similarity checks |
| psutil 7.0.0 | Available-memory checks, CPU-core detection, and process-tree memory monitoring |
| ONNX Runtime 1.20.1, tokenizers 0.21.0, NumPy 2.2.1 | Bundled embedding adapter and its supporting computation |
| PyInstaller 6.15.0 | Bundles Python, dependencies, GUI, and worker executables |
| NSISBI 3.12.3 | Builds the Windows installer and uninstall workflow |
| pytest 8.3.4 | Developer regression checks for generation, editing, exports, and failure cases |

These versions are declared in the desktop dependencies and asset manifest. They describe the checked repository configuration; an older installed bundle may contain an earlier implementation.

## 6. Editing, export, and reports

Generated content is stored as structured roles/projects plus editable section text. Once the user edits a section, the edited text is the export authority. Export does not rebuild the resume from stale model records over those edits.

Preview updates are scheduled after a 100 ms debounce, and autosave after a 500 ms debounce. These are timer settings, not measured guarantees for every laptop. Drafts use JSON files written through a temporary file followed by an atomic replacement. The app preserves a last-draft snapshot for recovery.

DOCX export uses the existing document renderer and reference-template formatting code through python-docx. HTML export builds a resume report and recalculates evidence from the current edited text. Neither export needs another model call. This desktop format does not add PDF export.

Named-technology keyword coverage is calculated separately from project text evidence. The capability review checks implementation facets such as synchronization directions, metadata mapping, or session-state storage. Its action/mechanism checks and term matching are local text heuristics.

The report distinguishes keyword presence from implementation evidence. Capability rows show supported, partial, or missing facets and include matching project passages. Known technical warnings and offline rule references are included. These results are reproducible heuristics; they do not establish an external ATS score or prove that fictional claims are true. Unknown technical combinations still need review.

## 7. Runtime ownership, memory, and local data

The controller permits one active job and one waiting job. Expensive work runs outside the interface process. Cancellation closes the owned worker process group and its model request; the Windows Job Object support helps contain child processes. The app does not reuse another application's model server.

The server binds to 127.0.0.1 on a dynamically allocated port. A generated session key protects requests to that server. The worker checks that the expected process owns the listener. No fixed external LLM API key or cloud subscription is needed for this path.

Model startup requires at least 2,300 MiB of available system RAM. The controller samples combined interface, worker, and descendant-process RSS and stops work if it observes more than 4 GiB. This is an application monitoring safeguard, not a reserved-memory allocation or an instantaneous operating-system hard limit. Processes run below normal priority, and an idle model is unloaded after five minutes.

Project Edition stores data under %LOCALAPPDATA%\ResumeOptimizerProjectEdition. This includes drafts, cached generation responses, artifacts, logs, and other runtime directories. Draft JSON can include the uploaded source text and JD. These are ordinary local files; the code does not add application-level encryption to them.

The Project Edition application identity, executable names, data folder, and mutex are separate from the legacy desktop edition. Installation files are bundled separately from user data, and the installer is designed to preserve saved data through upgrade and uninstall.

## 8. Measured results and verification

The locally validated build is Project Edition 1.1.0, using projects-quality-5. The acceptance run used the supplied nine-page PDF and 684-word Databricks JD with a fresh isolated cache profile and the final frozen worker.

| Measured item | Observed result |
| --- | --- |
| Complete generation | 392.31 seconds, approximately 6 minutes 32 seconds |
| Model submissions | 22: 19 base calls, one response-validation retry, and two quality repairs |
| Peak interface + worker + model memory | 2.15 GiB RSS |
| Editor handler | 1.0 ms |
| Preview plus autosave | 12.5 ms |
| Maximum Qt heartbeat gap | 104.6 ms |
| Active cancellation acknowledgement | 10.0 ms; owned processes gone after 500 ms |
| Regression checks | 67 passed, including all 46 legacy checks |

The host ran Windows 11 x64 build 26200 with approximately 16 GB RAM and 10 physical CPU cores; inference was limited to four threads and used no GPU. Installer compilation and other developer activity overlapped the run. These observations are not a benchmark on the target 8 GB laptop.

The same current rules were applied to the saved Databricks draft and the new draft:

| Local text measure | Saved draft | New draft |
| --- | ---: | ---: |
| Named required-technology keyword coverage | 88.0% | 100.0% |
| Required-technology project text evidence | 56.0% | 64.0% |
| Known technical/repetition warnings | 9 | 2 |

Keyword coverage can rise by adding valid names to the skills section. It does not establish that a project explains those skills well. The separate evidence and capability checks expose that difference. These figures are local measurements and are not external ATS scores.

Validation covered fresh generation, clean and edited DOCX/HTML exports, client/date sanitization, editing, undo/redo, autosave recovery, queue/cancellation behavior, missing/corrupt assets, low-memory handling, and coexistence. An isolated installer test passed install, upgrade, restart, export, and uninstall while preserving saved data and both existing app registrations. Compression was disabled for that lifecycle test; the production installer was compiled separately with the same payload and installation logic.

### Remaining limitations

The final sample still had 17 partial required-capability rows under the text rules, 2 known-pattern warnings, and 3 additional manual review notes. Those notes include ambiguous authentication component naming, confusion between partitioning and Z-ordering, and an accuracy/consistency comparison. Quality repairs are bounded, so unresolved issues remain visible for editing instead of triggering unlimited regeneration. The additional manual notes came from review of this acceptance sample; they are not proof that the automatic rules will detect every similar issue in future JDs.

The physically disconnected clean Windows installation/use test and the actual 8 GB, four-core reference-laptop benchmark remain release gates. An offline flag and a loopback-only connection sample do not establish that all required behavior was tested on a physically disconnected clean machine.

## 9. Build, installation, and source map

This document describes the current checked source, including the projects-quality-5 generation revision and schema-version-5 documents. The release installer is ResumeOptimizerProjectsSetup.exe. PyInstaller produces a directory bundle containing the GUI, worker, runtime, models, dependencies, and notices; NSIS packages that bundle for installation. The build script compiles to a staging path, preserves the previous installer, then writes the actual version, size, and SHA-256 into the release manifest and checksum file. The final frozen-worker run and installer checks are recorded in dist/ResumeOptimizerProjects-results.md. The physically disconnected clean-machine test and actual 8 GB reference-laptop benchmark remain external release gates. To update, close Project Edition, run the new installer, reopen the Project Edition shortcut, and generate a fresh resume to use the new generation workflow. Existing drafts remain readable and are not automatically regenerated over the user's edits. The legacy app keeps its separate identity and data.

Generation time depends on CPU, available RAM, prompt length, output length, retries, cache hits, and competing applications. The source configuration alone cannot guarantee an ATS percentage, generation duration, or peak memory on every 8 GB laptop.

| Source location, relative to the repository | What it explains |
| --- | --- |
| desktop/app.py, controller.py, worker.py | Interface, job queue, progress, cancellation, and worker protocol |
| desktop/project_generation.py | Project Edition planning, scoped prompts, structured calls, and repair budgets |
| desktop/generation.py | Shared source reader, Writer, response validation, and generation cache |
| desktop/project_rules.py, quality.py | Capability evidence, selected technical rules, normalization, and date removal |
| desktop/project_document.py, draft.py | Grouped project layout, client label, edited-text export, and reports |
| desktop/runtime.py, embedding.py | llama.cpp ownership/settings and the separate ONNX embedding adapter |
| desktop/storage.py, bootstrap.py, edition.py | Local paths, atomic snapshots, and edition identities |
| desktop/requirements.txt, desktop.spec, project_installer.nsi | Dependencies, executable bundling, and installer definition |
| build/desktop-assets/manifest.json | Exact model/runtime revisions, asset sizes, and checksums |

The source files and local asset manifest were the primary references for this overview. No live cloud service or external account was needed to produce it. Release measurements were taken from build/project-latest.json, build/project-quality-review.json, and dist/ResumeOptimizerProjects-results.md.
