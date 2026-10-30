# n8n workflow

`workflows/resume-optimize.json` is the active local resume-builder workflow.

## Flow

```text
Form -> /v1/ingest -> /v1/jd/extract -> /v1/optimize -> /v1/render -> Done
```

The public local form path is:

`http://localhost:5679/form/resume-optimize-v2`

## Import or update

1. Open `http://localhost:5679`.
2. Import `workflows/resume-optimize.json` if the workflow is not already present.
3. Activate the workflow using the toggle in the editor.

The workflow must be active for the human-readable form URL to work.

## Notes

- Use `http://api:8000` for API requests inside n8n containers; `localhost` refers to n8n itself.
- The optimize request has a 300-second timeout for local model generation.
- After editing the workflow in n8n, export it back to `workflows/resume-optimize.json` so the local source remains current.
