import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline import optimize  # noqa: E402
from schemas import Fact, Match, Requirement, RewriteOut  # noqa: E402
from validation import entity_guard  # noqa: E402


def test_empty_generation_reports_generation_failure(monkeypatch):
    import pytest
    monkeypatch.setattr(optimize.ideal_resume, "generate", lambda *args: "")
    with pytest.raises(ValueError, match="empty resume"):
        optimize.optimize([], [], [], set())

def test_profile_title_can_change_for_ideal_role(monkeypatch):
    fact = Fact(fact_id="F1", type="experience_bullet", text="Junior Engineer")
    monkeypatch.setattr(optimize.ideal_resume, "generate", lambda *args: "# Senior Backend Engineer")
    result = optimize.optimize([fact], [], [], set())
    assert "Senior Backend Engineer" in result.markdown
