# AI-Powered Resume Builder - Windows Desktop Application

This branch contains **Resume Optimizer Project Edition 1.6.3**, an offline Windows 11 x64 application using PySide6 and a local Qwen3-4B-Instruct-2507 Q4_K_M model through llama.cpp. The model and build artifacts are downloaded or built separately; see the [installation and build guide](docs/DESKTOP_INSTALLATION.md).

## Start here

- [Installation and build steps](docs/DESKTOP_INSTALLATION.md)
- [System and developer requirements](docs/DESKTOP_REQUIREMENTS.md)
- [How it works: methods, technologies, tools and models](docs/DESKTOP_TECHNICAL_OVERVIEW.md)
- [Local verification results and remaining limitations](desktop/PROJECT_TEST_RESULTS.md)

Choose a text PDF/DOCX, paste a job description, generate, edit, and save DOCX or an HTML report. Full fictional professional generation remains enabled; detected identity/contact and education qualifications are preserved. New documents have a six-bullet professional summary, bold skill categories and three project blocks under **Relevant Project Experience**, each headed **Company Name: #Confidential** and labelled **Role**. Calendar dates are omitted, including education dates; numeric experience such as **5+ years** remains. Existing drafts retain their versioned date behavior.

The installed application includes its Python/Qt runtime, CPU and CUDA inference servers, model assets and document renderer. Target users do not need Docker, n8n, Python, a cloud account, or a paid LLM API. Developer preparation downloads pinned assets once before packaging for offline installation.

**Source code is published here.** The installer and downloaded model weights are not stored in Git. Build `dist/ResumeOptimizerProjectsSetup.exe` using the installation guide; do not expect the old web-launcher EXE to install this edition.

The historical **1.1.0** benchmark completed full generation in **392.31 seconds**, using **22 model submissions** and **2.15 GiB peak application/worker/model RSS** on a 16 GB Windows host; these are historical measurements. See [full-stack verification](desktop/FULL_STACK_RESULTS.md) for current results and [Phase 1 verification](desktop/PHASE1_RESULTS.md) for earlier iterations. The 8 GB reference-laptop and clean physically disconnected Windows tests remain release gates. Reports show mandatory/preferred keyword presence separately from implementation evidence; they do not establish an external ATS score or verify fictional claims.

## General quality update

A shared JD brief drives distinct project ownership, complete six-bullet summaries,
bold skill categories and offline certification selection across roles. The report
separates mandatory/preferred evidence from keywords and identifies structured
summary fallback, missing credentials and technical review items. Existing drafts
and the previous installer are preserved. See [general quality verification](desktop/GENERAL_QUALITY_RESULTS.md).

The removed 2.3 GB startup gate remains removed; the 4 GiB runtime cap remains.
Mac hosting and GPU acceleration start only after output quality approval. The
planned host is an 8 GB Apple Silicon Mac, browser clients and a free tunnel;
see [Phase 2 decisions](desktop/MAC_HOSTING_PHASE2.md).

## Repository layout

| Path | Purpose |
| --- | --- |
| `desktop/` | Desktop UI, worker, model runtime, generation, packaging and tests |
| `api/` | Reused parsers, schemas, matching helpers and document rendering |
| `docs/DESKTOP_*.md` | Desktop installation, requirements and architecture |
| `desktop/fixtures/` | JD regression fixtures |
| `build/`, `dist/`, `models/` | Local generated assets, installers and weights; ignored by Git |

The other Docker/n8n/launcher files are retained from the base project. The desktop entrypoint is `desktop/project_main.py`; it directly reuses Python modules and does not start the web services.

The `final-version` branch contains the desktop implementation. Saved desktop data lives in `%LOCALAPPDATA%\ResumeOptimizerProjectEdition`, separately from the legacy desktop edition.

---

## Historical web application notes

The following notes describe the base web/launcher workflow, not the desktop entrypoint above.

A local application that turns a PDF or DOCX resume and a job description into a role-focused DOCX resume. FastAPI runs the processing pipeline, n8n provides the browser form, and a native `llama.cpp` server runs a GGUF language model.

The older web launcher workflow is described in [the historical setup guide](docs/SETUP_OTHER_PC.md); its prebuilt executable is not part of this source snapshot.

## Architecture

```text
Browser form (n8n)                          API clients
        |                                       |
        +------------------+--------------------+
                           |
                      FastAPI :8001
                           |
          +----------------+----------------+
          |                |                |
     Resume parser    JD extraction    Resume generation
     PDF / DOCX       requirements     Qwen3.5 4B GGUF
          |                |                |
          +----------------+----------------+
                           |
                   Markdown + DOCX render
                           |
                 data/runs/<run_id>/
```

Docker Compose starts the API and n8n containers on host ports 8001 and 5679. The launcher starts the GGUF server on the Windows host at port 18081, and the API reaches it at `host.docker.internal:18081`. n8n calls the API inside the Compose network at `http://api:8000`. Run artifacts are kept in `data/runs/`; n8n state and the Hugging Face embedding cache use Docker volumes.

## Workflow

The [n8n workflow](n8n/workflows/resume-optimize.json) accepts a resume file and job description, then calls these API stages:

1. `POST /v1/ingest` parses the resume and creates a run ID and fact ledger.
2. `POST /v1/jd/extract` extracts requirements from the full job description.
3. `POST /v1/optimize` generates and finalizes tailored Markdown, then records output coverage.
4. `POST /v1/render` creates the DOCX and HTML report. The completion page links to both.

The browser form is `http://localhost:5679/form/resume-optimize-v2`. On a fresh n8n installation, import and activate the workflow before using that URL. API documentation is at `http://localhost:8001/docs`; health status is at `http://localhost:8001/health`.

The active workflow uses **demo generation** (`fictional_template=true`, `fabrication_mode=demo`, `allow_unverified=true`). It can add plausible experience, projects, skills, and certifications. Generated claims are not verified against the source resume and must be reviewed before real use. The report's requirement coverage checks generated text; it does not verify candidate history.

## Technologies

| Component | Technology and role |
| --- | --- |
| API and schemas | Python 3.11, FastAPI, Pydantic, Uvicorn |
| Workflow and form | n8n, using the workflow JSON in this repository |
| Language model | Native `llama.cpp`; Qwen3.5 4B Q4_K_M GGUF for JD extraction and resume generation |
| Parsing and output | PyMuPDF for PDFs; `python-docx` for DOCX input and output |
| Matching | RapidFuzz, a local technology catalog, and optional `sentence-transformers` embeddings (`BAAI/bge-small-en-v1.5`) |
| Runtime and storage | Docker Compose, bind-mounted run data, and Docker volumes for n8n and model caches |
| Tests | pytest |

The embedding model loads on demand. If it is unavailable, matching falls back to lexical methods. Configuration is loaded from `.env`; start from [.env.example](.env.example). Downloaded GGUF models and generated files are separate from the Git repository.

## Project layout

```text
api/                FastAPI endpoints, parsers, matching, generation, rendering
api/resources/      Skill aliases and technology catalog
n8n/workflows/      Importable browser workflow
data/runs/          Local run artifacts and downloads
docs/               Setup and catalog documentation
eval/               Evaluation utilities
tests/              Automated tests
```

To build a launcher EXE on a Windows development machine with Python installed:

```powershell
.\launcher\build.ps1
```

Double-click `dist\ResumeOptimizerLauncher.exe` to install and run the application. The same built EXE is checked into `downloads/` for GitHub downloads. The [setup guide](docs/SETUP_OTHER_PC.md) covers another PC; the [local guide](docs/RUN_LOCALLY.md) covers checks and troubleshooting.

Keep `.env`, source resumes, job descriptions, models, and generated run artifacts out of version control.
