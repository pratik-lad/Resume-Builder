# Technology catalog

The API loads `api/resources/technology_catalog_base.json` (the existing 179-skill
dataset) plus the dated, source-reviewed additions in
`api/resources/technology_catalog.yaml`. The base entries extend name/alias
recognition but have no verified source metadata, so their descriptions are
not sent to the model. Only reviewed entries explicitly named in a JD can
enter the generation prompt, and their combined context is capped at 1,000
characters. The catalog is terminology support, not candidate evidence.

`CATALOG_ENABLED=false` turns off catalog vocabulary and prompt context for an
A/B comparison. Restart the API when changing it because the matching index
is built at startup.
The current model, fabrication settings, system prompt, API, and n8n workflow
remain unchanged.

Audit the catalog from the repository root:

```powershell
$env:PYTHONPATH = "api"
python -m matching.technology_catalog --jd "C:\path\to\job-description.docx"
```

The audit reports terms found in the JD but missing from the catalog,
duplicate surfaces, conflicts with the pre-existing alias map, entries without
source/review metadata, and entries older than the catalog's 180-day review
window. Existing aliases take precedence; the current PySpark-to-Spark mapping
is intentionally unchanged and reported as a conflict.

For maintenance, add or update an entry in the reviewed YAML only after
checking the vendor or project's official documentation. Record the canonical
name, aliases, category, short definition, source URL, and review date. Run
`tests/test_technology_catalog.py` and the wider test suite. A snapshot is
finite; it cannot promise to include every newly released product. Review
the audit at least every 180 days and after a JD exposes a missing tool.
