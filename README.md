# Resume Optimizer POC

## Purpose

This is a local resume-builder and JD-tailoring POC. A user uploads a resume (PDF or DOCX) and pastes a job description (JD). The system uses local Ollama model `dolphin-llama3` to create a concise, ATS-readable tailored resume, then produces a DOCX download and an HTML report containing the extracted JD requirements.

This document is the current handoff context for a coding agent. Prefer it over old assumptions about a source-claim-only optimizer or a UCR safety-gated workflow.

## Status and scope

**Status: working local POC / internal beta; not production-ready.**

The active product goal is strong JD tailoring: summary, skills, project descriptions, and responsibilities should reflect the complete JD. The system deliberately does not use the older match/score/strategy safety gates in the active n8n path.

The generated resume uses the uploaded candidate's name, education, employment identities, and employment dates. It rewrites the summary, skills, responsibilities, and projects for the JD while keeping independent source jobs and projects separate.

Do not reintroduce the retired per-bullet validation, UCR blocking, low-fit branching, or n8n safety gates unless explicitly requested.

## Active architecture

```text
Browser
  -> n8n form
  -> POST /v1/ingest
  -> POST /v1/jd/extract
  -> POST /v1/optimize
  -> POST /v1/render
  -> DOCX download + HTML report

FastAPI -> local Ollama at host.docker.internal:11434
          model: dolphin-llama3
```

Active form: `http://localhost:5678/form/resume-optimize-v2`  
API health: `http://localhost:8000/health`

The active workflow export is `n8n/workflows/resume-optimize.json`. Its sequence must remain:

`Form -> ingest -> jd/extract -> optimize -> render -> Done`

The API also exposes older matching, strategy, review, project-bridge, and dataset endpoints. These are optional legacy utilities and are **not called by the active n8n workflow**. Do not delete them casually: they are imported by `api/main.py` and covered by tests.

## Main code map

| File | Responsibility |
|---|---|
| `api/main.py` | FastAPI endpoints, run storage, caching, active stage orchestration |
| `api/pipeline/ingest.py` | Parse resume, extract facts, determine source employment entries/dates |
| `api/pipeline/jd.py` | Extract complete JD requirements and canonical skills |
| `api/pipeline/optimize.py` | Build compact generation input and call the resume builder/finalizer |
| `api/pipeline/ideal_resume.py` | Dolphin prompt, structural repair decision, output finalizer, experience formatting |
| `api/pipeline/render.py` | DOCX and report assembly |
| `api/docgen/reference_template.py` | Active DOCX template renderer |
| `api/llm/client.py` | Non-streaming Ollama `/api/chat` client |
| `api/config.py` / `.env` | Runtime configuration |
| `n8n/workflows/resume-optimize.json` | Active form workflow |

## Current generation contract

### Inputs

- Resume: `.pdf` or `.docx`
- Full JD text
- Model: `dolphin-llama3`
- Rewrite temperature: `0.15`

### Resume output requirements

The generator/finalizer should produce Markdown with a clear structure similar to:

```text
# Candidate Name
Target Role
Contact details

## Professional Summary
## Technical Skills
## Professional Experience
Total Professional Experience: X Years Y Months
### Job Title | Company
Start Date - End Date/Present
## Selected Projects
### Project Name
## Education
```

Expected behavior:

- Extract and reflect all important JD skills, tools, responsibilities, qualifications, and preferences.
- Preserve distinct jobs and projects as distinct subheadings; never collapse them into one bullet list.
- Build a targeted professional summary and technical-skills block.
- Include exactly one substantial JD-aligned project in `Selected Projects` when required by the current prompt.
- Keep source employment headings, companies, titles, and dates sourced from the uploaded resume.
- Use relevant project experience when the uploaded resume has no employment entry.
- Never list the target company as an employer unless it exists in the source resume.

### Output cleanup and repair behavior

`ideal_resume.finalize()` is the final protection before DOCX rendering. It:

- Normalizes heading aliases (`Profile Summary` -> `Professional Summary`, `Projects` -> `Selected Projects`).
- Merges duplicate top-level sections and deduplicates repeated lines.
- Adds the extracted JD technology surface to `Technical Skills`.
- Removes artifacts such as `<think>...</think>`, Markdown fences, prompt echoes, repair narration, `Missing Sections`, and `New Project Misplaced or Missing`.
- Rebuilds professional-experience identity and duration from `ExperienceEntry` data when source entries are available.

The model may receive one repair request only for real structural failures: required sections missing or the required new project missing/misplaced. Missing skill keywords alone must **not** cause another LLM call because the finalizer supplies them deterministically.

## Performance decisions

Current values are in `.env` and `api/config.py`:

| Variable | Value | Reason |
|---|---:|---|
| `MODEL_EXTRACT` | `dolphin-llama3` | JD extraction |
| `MODEL_REWRITE` | `dolphin-llama3` | Final resume generation |
| `NUM_CTX` | `6144` | Local latency/context trade-off |
| `MAX_RESUME_TOKENS` | `1800` | Concise approximately two-page output |
| `TEMP_EXTRACT` | `0.0` | Stable JD extraction |
| `TEMP_REWRITE` | `0.15` | Stable resume generation |
| `LLM_TIMEOUT` | `280` seconds | Allows a single local generation to complete |

Prompt efficiency rules:

- The complete JD is sent once.
- Extracted requirements already appearing verbatim in the JD are not appended again.
- Only missing normalized requirements are appended under `ADDITIONAL EXTRACTED REQUIREMENTS`.
- Do not restore the old dynamic oversized context calculation; use the configured `NUM_CTX`.

Typical end-to-end local time:

- 1–2 page resume: 60–150 seconds.
- Dense 5-page resume: 2–4 minutes.
- Cold model loading, CPU inference, and very long JDs may take longer.

## Run and verify

Prerequisites: Docker Desktop, native Ollama on the host, and the required model.

```powershell
ollama pull dolphin-llama3
docker compose up -d --build
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
```

After API or `.env` changes:

```powershell
docker compose up -d --build api
```

Run regression tests:

```powershell
pytest -q
```

For a focused check of resume generation/finalization:

```powershell
pytest tests/test_ideal_resume.py tests/test_tailoring_finalizer.py -q
```

## Important regression scenarios

Do not break these behaviors:

1. `Projects` and `Selected Projects` are equivalent for repair detection.
2. `New JD-Aligned Project` counts as the required new project.
3. Repair diagnostics and conversational text never appear in the DOCX.
4. Existing projects remain separate.
5. A fake target-company employer must not survive when source dated employment is available.
6. Total experience is calculated from non-overlapping source date intervals, not the JD's years requirement.
7. The full JD requirement surface remains visible in the final technical-skills block.
8. A JD-only keyword gap does not trigger a second expensive model generation.

## Storage and cache behavior

- Each submission receives a `run_id`.
- Files and generated artifacts are written to `data/runs/<run_id>/`.
- Resume and JD extraction results are cached under `data/cache/`.
- Optimization caches by source resume text, extracted JD requirements, model name, and prompt version.
- Bump `PROMPT_VERSION` after changing prompt/generation behavior.
- Bump `FINALIZER_VERSION` after changing finalization behavior so cached Markdown is re-finalized.
- Do not delete `data/runs/` or `data/cache/` during normal cleanup: they contain user artifacts and useful cache data.

## Known limitations

- This is generative tailoring. It cannot independently verify that every newly written responsibility occurred in the candidate's real work.
- Source-experience parsing needs explicit recognizable date ranges. Complex or unusual date layouts may need parser improvements.
- A very dense resume plus a long JD can exceed the practical 6,144-token budget; older/repetitive material can be compressed.
- The current browser request is synchronous. Large jobs can still approach the n8n 300-second optimize timeout.
- There is no authentication, tenant isolation, malware scanning, retention policy, encrypted artifact store, observability stack, or production-grade retry queue.
- The project is not ready for a public internet deployment or paid use.

## Recommended next work

Priority order:

1. Build a labelled evaluation set of 30–50 diverse resume/JD pairs.
2. Record quality review results and p50/p95 latency by stage and resume size.
3. Move generation to an asynchronous job queue with progress, retries, and completion notification.
4. Add authentication, upload validation/scanning, artifact retention/deletion, encryption, rate limits, logs, metrics, and alerts.
5. Test parser and DOCX output against a broad set of real resume layouts and ATS-style round trips.
6. Fine-tune only after evaluation demonstrates a repeatable deficiency that prompt/finalizer changes cannot solve.

Use `eval/README.md` and `eval/tailoring_cases.template.jsonl` for the current review format.

## Cleanup policy

The current repository intentionally retains optional legacy modules and tests because they are still importable API functionality. The old safety-architecture, evaluation, fine-tuning READMEs, and unused n8n workflow snapshots have already been removed. Do not delete Python modules merely because the active n8n path does not call them without first removing their API routes/imports and validating the full test suite.
