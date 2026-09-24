# Human review guide

## Review through /review

Open http://localhost:8000/review. Every requirement loads its proposed status,
method, supporting facts and stored score. Facts are preselected. The original
proposal is available under the provenance disclosure. All unapproved values
are labelled **PROPOSED — NOT GOLD**. Missing numeric scores in older proposals
are shown as not stored; they are not reconstructed as if they were original.
On acceptance, an absent score uses the documented representative value of
1.0 (covered), 0.55 (partial), or 0.0 (missing). An existing score is preserved
and must agree with its status.

- **ACCEPT** validates the displayed annotation and writes the four gold fields
  and your decision into the evaluation CSV. This is the only gold-writing action.
- **EDIT** enables corrections. **ACCEPT EDITS** then validates and saves.
- **REJECT** records rejection without writing or deleting existing gold fields.
- **Save progress** writes an incomplete draft into `review_states/`, separate
  from gold. Drafts take precedence on reload, including your decision and notes.

Fact IDs and requirement IDs are linked automatically. Removing a requirement
does not move its evidence to another requirement. Validation also checks source
phrases, skill aliases, status/score consistency and entity provenance. It cannot
prove that a semantic match is true: verify the cited evidence yourself.

Technical skill requirements are `hard_skill` (including Java, Spring Boot,
Microservices, Kafka, PostgreSQL, REST APIs, design patterns and data structures).
Degrees, explicit years and certifications are `qualification`. An activity
such as building an application can remain `responsibility`. Optional items
retain `must_have=false`. Known combined skill requirements are split into
separate source phrases; check other complex natural-language expectations for
atomicity during review.

`AWS / Azure / GCP` is one alternatives group (`logic=any`): one supported
alternative can cover it. `Docker & Kubernetes` becomes two rows, each retaining
its original required/optional flag. `CI/CD` is a single name, not an OR group.
Parenthesized examples are not automatically converted into mandatory skills.
The original source sentence is retained as `source_text` when a row is split.

Pair 1's Partial decision remains a proposal. Nothing is accepted merely by
loading the page, editing, or saving progress.

This CSV is a review queue, not a gold dataset yet. Do not replace a blank
`gold_*` cell with a proposal, inferred claim, or a skill that is only present
in the job description. Use JSON in the four `gold_*` columns. Keep the
existing `proposed_*` and `existing_label_*` cells as evidence of what was
proposed; they are not the review decision.

## CSV columns

| Column | Meaning | Reviewer action |
| --- | --- | --- |
| `resume_id` | ID of the selected structured resume profile. | Do not edit. Locate the profile in `synthetic_profiles.json`. |
| `jd_id` | ID of the selected JD. | Do not edit. Locate it in `scraped_jobs.json` (or `benchmarks.json` when applicable). |
| `selection_group` | Why the pair is in the review set. | Do not edit. |
| `pair_source` | Source files from which the pair was selected. | Do not edit. |
| `proposed_fit_label` | Initial heuristic or imported-label proposal. | Do not treat as gold or overwrite it. |
| `proposed_matches` | Imported candidate matches, when an external model label included them. | Verify independently; it can be wrong or incomplete. |
| `proposed_missing_requirements` | Imported candidate gaps, when available. | Verify independently; it can be wrong or incomplete. |
| `existing_label_evidence` | Existing aggregate component scores, if present. | Use only as comparison evidence, never as project gold. |
| `existing_label_provenance` | Origin of the proposal. | Use to judge how much independent review is needed. |
| `gold_facts` | Resume evidence annotation. | Fill with the JSON array described below. |
| `gold_requirements` | JD requirement annotation. | Fill with the JSON array described below. |
| `gold_matches` | Requirement-to-resume-evidence annotation. | Fill with the JSON array described below. |
| `gold_entities` | Resume entity whitelist and fact-level entity check. | Fill with the JSON object described below. |
| `review_status` | Review state and final fit decision. | Set to `reviewed_match`, `reviewed_partial`, or `reviewed_mismatch` only after all four gold cells are complete. Otherwise retain `needs_human_review`. |
| `confidence` | Confidence in your completed annotation, not in the imported label. | Use `high`, `medium`, or `low`. Explain low confidence in notes. |
| `review_notes` | Short evidence-based explanation, ambiguity, or decision rationale. | Update during review. |

## Evidence to use

For the resume profile, use only the fields on that profile in
`synthetic_profiles.json`: `roles`, `skills_primary`, `skills_secondary`,
`experience_years`, `seniority`, `domains`, and location preferences. These
profiles are the resume-side source for this 50-pair matching set. Do not infer
a missing skill from a role title and do not import a JD skill into the resume.

For the JD, use its `title` and `description` in `scraped_jobs.json`. Mark a
requirement as must-have only when the JD explicitly signals required/mandatory
language or makes it essential to the role. Preferred, bonus, nice-to-have, or
optional language is `must_have: false`. Do not turn company marketing, equal
opportunity text, or generic boilerplate into a requirement.

Use existing score labels and Phase 3 model labels only after making an
independent annotation. They are comparison evidence, not a shortcut.

## Required JSON formats

Keep JSON on one line in each CSV cell. Use double quotes for JSON strings.
IDs must be stable within the row: facts use `F01`, `F02`, etc.; requirements
use `R01`, `R02`, etc. A reviewer may choose a different consistent prefix, but
the `fact_ids` and `req_id` references in `gold_matches` must match exactly.

### `gold_facts`

JSON array of resume-side facts. Each fact must quote or faithfully restate one
source-profile field without adding a claim.

```json
[
  {
    "fact_id": "F01",
    "type": "skill",
    "parent_id": "skills_primary",
    "context": "skills_primary",
    "text": "Python",
    "entities": {"tech": ["Python"], "orgs": [], "numbers": [], "dates": []},
    "source": {"page": 1, "char_start": 0, "char_end": 0}
  },
  {
    "fact_id": "F02",
    "type": "summary",
    "parent_id": "experience_years",
    "context": "experience_years",
    "text": "3 years of experience",
    "entities": {"tech": [], "orgs": [], "numbers": ["3"], "dates": []},
    "source": {"page": 1, "char_start": 0, "char_end": 0}
  }
]
```

Allowed `type` values: `experience_bullet`, `project_bullet`, `skill`,
`education`, `certification`, `summary`, `other`. In this structured-profile
set, `skill`, `summary`, `experience_bullet`, and `other` will be most common.
The zero source offsets are intentional: structured profile records have no PDF
page spans.

### `gold_requirements`

JSON array of independently extracted JD requirements.

```json
[
  {
    "req_id": "R01",
    "text": "Build and maintain REST APIs in Python",
    "type": "hard_skill",
    "must_have": true,
    "min_years": 2,
    "canonical_skills": ["python", "rest api"],
    "weight": 3.0
  }
]
```

Allowed `type` values: `hard_skill`, `tool`, `responsibility`,
`qualification`, `soft_skill`. Use `min_years: 0` when the JD gives no minimum.
Use `weight: 3.0` when `must_have` is true and `weight: 1.0` when it is false;
these are the project's configured extraction weights. Preserve the JD's actual
requirement text in `text`; use
`canonical_skills` only for the normalized technology or concept names.

### `gold_matches`

JSON array with one entry for every `gold_requirements` item. It links a
requirement to zero or more verified resume facts.

```json
[
  {
    "req_id": "R01",
    "fact_ids": ["F01"],
    "score": 1.0,
    "method": "lexical",
    "status": "covered"
  },
  {
    "req_id": "R02",
    "fact_ids": [],
    "score": 0.0,
    "method": "none",
    "status": "missing"
  }
]
```

Use `covered` for direct, sufficient evidence; `partial` for related but
incomplete evidence; and `missing` when there is no evidence. Scores from
`0.75` through `1.0` are covered, `0.40` up to `0.75` (exclusive) are partial,
and below `0.40` are missing. Preserve a stored proposal score if accepting it.
`method` must be one of `lexical`, `fuzzy`, `semantic`, `none`,
`qualification:degree`, `qualification:years`,
`qualification:degree+years`, or `qualification:certification`. Choose
`lexical` for explicit skill evidence, `semantic` for a genuine paraphrase,
the relevant `qualification:*` method for rule-based evidence, and `none` for
missing evidence. Do not use semantic similarity to claim that two unrelated
technical tools match.

### `gold_entities`

JSON object recording the exact resume-side entity whitelist used for
hallucination checking and a fact-level verification map. The entity names must
be present in the reviewed profile facts; do not add JD-only technologies.

```json
{
  "allowed_entities": ["Python", "PostgreSQL", "3"],
  "by_fact_id": {
    "F01": {"tech": ["Python"], "orgs": [], "numbers": [], "dates": []},
    "F02": {"tech": [], "orgs": [], "numbers": ["3"], "dates": []}
  }
}
```

The `by_fact_id` entity values should agree with the same fact's `entities`
field in `gold_facts`. This explicit duplicate is deliberate: it makes the
validator whitelist reviewable without searching through a long facts cell.

## Overall pair decision

Keep `proposed_fit_label` unchanged. Record the final decision in
`review_status`:

- `reviewed_match`: all core must-have skills/responsibilities are covered and
  stated qualifications are covered or not applicable. Optional gaps may remain.
- `reviewed_partial`: there is credible, material overlap, but one or more
  meaningful must-haves, seniority expectations, or qualifications are partial
  or missing.
- `reviewed_mismatch`: the profile lacks the core domain/skills/responsibilities
  needed for the role, or most decisive must-haves are missing. A shared generic
  word, location, or soft skill alone is not a match.

## Per-pair checklist

1. Open the profile by `resume_id` and JD by `jd_id`; ignore the proposal until
   you have read both sources.
2. Add only source-supported resume facts to `gold_facts` and their entities to
   `gold_entities`.
3. Extract atomic JD requirements into `gold_requirements`; distinguish required
   from preferred.
4. Add exactly one match record per requirement. Cite only fact IDs that support
   that requirement.
5. Decide match, partial, or mismatch from the must-have evidence, then set the
   corresponding `review_status`.
6. Set confidence and capture ambiguity in `review_notes`.
7. Before saving, verify every `gold_matches.req_id` exists in
   `gold_requirements`, every `fact_id` exists in `gold_facts`, and no entity
   appears only in the JD.
