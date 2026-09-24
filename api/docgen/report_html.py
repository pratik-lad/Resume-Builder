"""Score card page. Shows before/after, the gap report, and the validation log.

The gap report is a first-class feature, not an apology: it is the honest half of
the contract. We tell you what's missing instead of inventing it.
"""
from html import escape

from schemas import GapReport, OptimizeResult, ScoreCard

_CSS = """
:root{--bg:#fff;--fg:#1a1a1a;--mut:#666;--line:#e5e5e5;--ok:#0a7d33;--warn:#b25000;--bad:#b00020}
@media(prefers-color-scheme:dark){:root{--bg:#161616;--fg:#eee;--mut:#aaa;--line:#333}}
body{background:var(--bg);color:var(--fg);font:15px/1.55 system-ui,sans-serif;max-width:820px;margin:0 auto;padding:32px 20px}
h1{font-size:22px;margin:0 0 4px}h2{font-size:16px;margin:28px 0 8px}
.sub{color:var(--mut);font-size:13px;margin-bottom:24px}
.big{font-size:40px;font-weight:700}.delta{font-size:18px;color:var(--ok);margin-left:10px}
table{border-collapse:collapse;width:100%;margin:8px 0}
td,th{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;font-size:14px}
th{color:var(--mut);font-weight:600}
.pill{display:inline-block;padding:2px 8px;border-radius:10px;font-size:12px}
.ucr{background:var(--ok);color:#fff}.ucrbad{background:var(--bad);color:#fff}
.miss{color:var(--bad)}.part{color:var(--warn)}
.note{border-left:3px solid var(--line);padding:8px 12px;color:var(--mut);font-size:13px;margin:12px 0}
"""


def _rows(card: ScoreCard) -> str:
    pairs = [("Hard skill coverage", card.hard_skill_coverage),
             ("Responsibility match", card.responsibility_match),
             ("Qualification match", card.qualification_match),
             ("Keyword surface", card.keyword_surface)]
    return "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pairs)


def render(run_id: str, before: ScoreCard, after: ScoreCard, gap: GapReport,
           result: OptimizeResult, role_title: str = "") -> str:
    delta = round(after.jd_alignment_score - before.jd_alignment_score, 1)
    ucr_cls = "ucr" if result.ucr == 0 else "ucrbad"

    missing = "".join(
        f"<tr><td class='miss'>{g.requirement}</td><td>{'required' if g.must_have else 'preferred'}</td>"
        f"<td>{g.score}</td></tr>"
        for g in gap.missing_required + gap.missing_optional) or "<tr><td colspan=3>None</td></tr>"

    partial = "".join(
        f"<tr><td class='part'>{g.requirement}</td><td>{g.evidence[:90]}</td><td>{g.score}</td></tr>"
        for g in gap.partial) or "<tr><td colspan=3>None</td></tr>"

    log = "".join(
        f"<tr><td>{r.fact_id}</td><td>{r.status}</td><td>{r.attempts}</td>"
        f"<td>{'; '.join(r.violations_fixed)[:120]}</td></tr>"
        for r in result.rewrites)

    strategy = result.strategy
    coverage = ""
    changes = ""
    potential = after.jd_alignment_score
    bridged = after.jd_alignment_score
    must_coverage = 0.0
    limitations = ""
    transferable = ""
    experience_gaps = ""
    keywords = ""
    if strategy:
        potential = strategy.potential_score_existing_evidence
        bridged = strategy.project_bridged_projected_alignment
        must_coverage = strategy.must_have_coverage
        coverage = "".join(
            f"<tr><td>{escape(c.requirement)}</td><td>{c.importance}</td><td>{c.status}</td>"
            f"<td>{escape('; '.join(c.evidence)[:160])}</td><td>{escape(c.improvement_opportunity)}</td></tr>"
            for c in strategy.coverage)
        changes = "".join(f"<li><b>{a.target}</b>: {escape(a.reason)}</li>" for a in strategy.actions)
        limitations = "".join(f"<li>{escape(item)}</li>" for item in strategy.limitations)
        transferable = "".join(f"<li>{escape(item)}</li>" for item in strategy.transferable_skills) or "<li>No directly matched skill facts were identified.</li>"
        experience_gaps = "".join(
            f"<tr><td>{escape(item.requirement)}</td><td>{item.required_years} years</td>"
            f"<td>{item.qualification_result}; "
            f"{item.verified_relevant_months if item.verified_relevant_months is not None else 'no verified'} months "
            f"from explicit employment dates</td>"
            f"<td>{item.gap_years if item.gap_years is not None else 'cannot calculate from source'}</td></tr>"
            for item in strategy.experience_gaps) or "<tr><td colspan=4>No explicit JD years requirement.</td></tr>"
        keywords = ", ".join(escape(item) for item in strategy.keyword_priorities) or "None"

    bridge = result.project_bridge
    project_html = "<p>No project bridge is needed for the current required gaps.</p>"
    if bridge:
        project_html = f"""
<div class="note"><b>PROPOSED PROJECT &mdash; NOT YET COMPLETED</b><br>
This is future work and is not included in the optimized resume.</div>
<h3>{escape(bridge.title)}</h3>
<p><b>Status:</b> {bridge.status} &middot; <b>Eligible as resume evidence:</b> {str(bridge.eligible_as_resume_evidence).lower()}</p>
<p>{escape(bridge.problem_statement)}</p>
<p><b>Why it matches:</b> {escape(bridge.why_it_matches_jd)}</p>
<p><b>Technologies to learn/use:</b> {escape(', '.join(bridge.technologies) or 'Defined during implementation')}</p>
<p><b>Requirements targeted:</b></p><ul>{''.join(f'<li>{escape(x)}</li>' for x in bridge.requirements_covered)}</ul>
<p><b>Features:</b></p><ul>{''.join(f'<li>{escape(x)}</li>' for x in bridge.features)}</ul>
<p><b>Implementation roadmap:</b></p><ol>{''.join(f'<li>{escape(x)}</li>' for x in bridge.implementation_roadmap)}</ol>
<p><b>Testing:</b></p><ul>{''.join(f'<li>{escape(x)}</li>' for x in bridge.testing_plan)}</ul>
<p><b>Deployment:</b></p><ul>{''.join(f'<li>{escape(x)}</li>' for x in bridge.deployment_plan)}</ul>
<p><b>GitHub structure:</b> {escape(', '.join(bridge.github_structure))}</p>"""

    truth = result.truth_report
    truth_html = ""
    if truth:
        truth_html = f"""<p>Current resume claims source-supported: <b>{str(truth.current_resume_claims_source_supported).lower()}</b><br>
Proposed project separated: <b>{str(truth.proposed_project_separated).lower()}</b><br>
Proposed project used as current evidence: <b>{str(truth.proposed_project_used_as_evidence).lower()}</b><br>
Immutable fields preserved: <b>{str(truth.immutable_fields_preserved).lower()}</b></p>
<ul>{''.join(f'<li>{escape(x)}</li>' for x in truth.notes)}</ul>"""

    return f"""<!doctype html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Run {run_id}</title><style>{_CSS}</style></head><body>
<h1>JD Alignment Report{' &mdash; ' + role_title if role_title else ''}</h1>
<p class="sub">Run {run_id}. An internal relevance measure &mdash; not an ATS simulation.</p>

<div><span class="big">{after.jd_alignment_score}</span>
<span class="delta">{'+' if delta >= 0 else ''}{delta} from {before.jd_alignment_score}</span></div>
<p><span class="pill {ucr_cls}">Unsupported Claim Rate: {result.ucr}</span>
&nbsp; {result.accepted} genuinely rewritten &middot; {result.unchanged} model kept as-is
&middot; {result.reverted} reverted after failed validation</p>

<h2>Sub-scores (after)</h2><table><tr><th>Component</th><th>Score</th></tr>{_rows(after)}</table>

<h2>Truthful optimization ceiling</h2>
<p>Must-have coverage: <b>{must_coverage}%</b><br>
Current JD alignment: <b>{before.jd_alignment_score}</b><br>
Optimized current-evidence alignment: <b>{after.jd_alignment_score}</b><br>
Existing-evidence presentation ceiling: <b>{potential}</b><br>
Project-bridged projected alignment: <b>{bridged}</b> <em>(only after real completion and verification; not current alignment)</em></p>
<ul>{limitations}</ul>

<h2>Requirement coverage</h2>
<table><tr><th>Requirement</th><th>Importance</th><th>Status</th><th>Evidence</th><th>Opportunity</th></tr>{coverage}</table>

<h2>Optimization changes</h2><ul>{changes}</ul>
<p><b>Priority JD terminology already supported by evidence:</b> {keywords}</p>

<h2>Transferable skills</h2><ul>{transferable}</ul>

<h2>Experience gap</h2>
<div class="note">Professional years are reported from explicit source evidence only. Projects never add professional years.</div>
<table><tr><th>JD requirement</th><th>Required</th><th>Verified source-date result</th><th>Gap</th></tr>{experience_gaps}</table>

<h2>Gaps &mdash; not added to your resume</h2>
<div class="note">These requirements have no support in your resume. Add them yourself
if you genuinely have the experience. This system will not fabricate them.</div>
<table><tr><th>Requirement</th><th>Priority</th><th>Score</th></tr>{missing}</table>

<h2>Partial matches &mdash; worth expanding</h2>
<table><tr><th>Requirement</th><th>Your evidence</th><th>Score</th></tr>{partial}</table>

<h2>Validation log</h2>
<table><tr><th>Fact</th><th>Status</th><th>Attempts</th><th>Violations caught</th></tr>{log}</table>

<h2>Project bridge</h2>{project_html}

<h2>Truth and safety report</h2>{truth_html}

<p class="sub" style="margin-top:28px"><a href="/v1/download/{run_id}">Download optimized resume (.docx)</a></p>
</body></html>"""
