import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from llm import structured  # noqa: E402
from pipeline import optimize  # noqa: E402
from schemas import Fact, Match, Requirement, RewriteOut  # noqa: E402
from validation import entity_guard  # noqa: E402


def test_structured_trace_captures_raw_parsed_and_latency(monkeypatch):
    monkeypatch.setattr(structured, "chat", lambda **kwargs: '{"text":"Built Python API","used_evidence":true}')
    parsed, trace = structured.generate_with_trace("prompt", RewriteOut)
    assert parsed.text == "Built Python API"
    assert trace[0]["raw_model_output"]
    assert trace[0]["parsed_output"] == parsed.model_dump()
    assert isinstance(trace[0]["latency_ms"], float)


def test_ideal_debug_records_mode_without_validation(monkeypatch):
    monkeypatch.setattr(optimize.ideal_resume, "generate", lambda *args: "## Skills\nPython")
    debug = {}
    result = optimize.optimize([], [], [], set(), debug=debug)
    assert "Python" in result.markdown
    assert "## Professional Summary" in result.markdown
    assert debug["generation_mode"] == "resume_builder_tailoring"
    assert debug["validation_performed"] is False
    assert debug["requirement_count"] == 0

def test_skills_do_not_require_matched_rewrite_candidates(monkeypatch):
    fact = Fact(fact_id="F1", type="skill", text="Python")
    req = Requirement(req_id="R1", text="FastAPI", type="hard_skill", must_have=True)
    calls = []
    monkeypatch.setattr(optimize.ideal_resume, "generate",
                        lambda jd, background: (calls.append(jd) or "## Skills\nFastAPI"))
    debug = {}
    result = optimize.optimize([fact], [req], [], set(), debug=debug)
    assert "FastAPI" in calls[0] and "FastAPI" in result.markdown
    assert debug["requirement_count"] == 1
