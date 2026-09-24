"""Stage 5: assemble the final document and the report page."""
from pathlib import Path
from html import escape
import re
from docx import Document

from docgen import docx_builder, report_html, reference_template
from schemas import (Fact, GapReport, OptimizationStrategy, OptimizeResult, Rewrite, ScoreCard)
from validation.immutable_guard import contact_values


def build_ideal_docx(markdown: str, out_path: Path) -> Path:
    """Use the refined professional template for all new exports."""
    return reference_template.build(markdown, out_path)


def build_ideal_report(markdown: str, req_set) -> str:
    rows = "".join(
        f"<tr><td>{escape(r.req_id)}</td><td>{escape(r.text)}</td>"
        f"<td>{'Required' if r.must_have else 'Preferred'}</td></tr>"
        for r in req_set.requirements)
    return ("<!doctype html><html><head><meta charset='utf-8'>"
            "<title>Tailored resume</title><style>body{max-width:900px;margin:40px auto;"
            "font:16px/1.6 system-ui}pre{white-space:pre-wrap}td{padding:8px}</style>"
            "</head><body><h1>Tailored resume</h1>"
            f"<pre>{escape(markdown)}</pre><h2>Full JD extraction</h2>"
            f"<table>{rows}</table><h2>Original job description</h2>"
            f"<pre>{escape(req_set.jd_text)}</pre></body></html>")


def header_lines(raw_text: str) -> list[str]:
    """Name plus literal source contact values, kept immutable by the renderer."""
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    return ([lines[0]] if lines else []) + contact_values(raw_text)


def build_docx(facts: list[Fact], rewrites: list[Rewrite], raw_text: str,
               strategy: OptimizationStrategy | None,
               out_path: Path) -> Path:
    return docx_builder.build_from_source(raw_text, rewrites, out_path)


def build_report(run_id: str, before: ScoreCard, after: ScoreCard, gap: GapReport,
                 result: OptimizeResult, role_title: str = "") -> str:
    return report_html.render(run_id, before, after, gap, result, role_title)
