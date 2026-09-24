# Tailoring evaluation set

This folder contains the evaluation format for the current resume-builder workflow. It is not the retired match-score evaluation system.

## Goal

Collect 30–50 reviewed cases in the form:

`source resume + full JD -> generated resume -> human review`

Use a mix of one-page, five-page, two-column, table-heavy, fresher, internship, and multi-employer resumes. Never store private resumes in a public repository; use consented, redacted, or synthetic fixtures.

## Case format

Copy `tailoring_cases.template.jsonl` to a private local file and add one JSON object per case. Reference a resume fixture or a local run ID instead of embedding sensitive resume text. `sample_cases.pending_review.jsonl` is the initial 17-case manifest prepared from the supplied Sample JD and Sample resumes folders; it contains source expectations, but no generated output is marked approved.

Use `verified` when source employment dates are clear, `editable_placeholder` when an employment role has unclear dates, and `not_applicable` when the source resume has no employment history.

Each case must record these review outcomes:

- identity, education, employer, and date preservation;
- total-experience correctness or editable-date placeholder behavior;
- structural integrity for separate projects/jobs;
- absence of model artifacts or conversational text;
- JD technology coverage in Technical Skills;
- reviewer approval and concrete notes;
- stage latency measurements.

## Acceptance targets before fine-tuning

Start with a measured baseline. Do not fine-tune until at least 30 reviewed cases exist.

| Metric | Initial target |
|---|---:|
| Identity/education preserved | 100% |
| Employer/date preservation or editable placeholder | 100% |
| No leaked model artifacts | 100% |
| Independent projects retained | 95%+ |
| JD technology coverage | 95%+ |
| Reviewer-approved output | 85%+ |

Record p50/p95 time separately for ingest, JD extraction, optimize, and render. A fine-tuned model should improve a measured weakness without reducing the preservation metrics.
