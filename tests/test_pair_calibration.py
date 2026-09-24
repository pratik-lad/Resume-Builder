import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from matching import scorer  # noqa: E402
from schemas import Match  # noqa: E402


def covered(n):
    return [Match(req_id=f"R{i}", score=1, status="covered", method="lexical") for i in range(n)]


def test_calibrated_pair_decision_uses_multiple_evidence_signals():
    assert scorer._pair_decision(63.1, 58.3, 23.8, covered(6))[0] == "match"
    assert scorer._pair_decision(15.0, 25.0, 0.0, [Match(req_id="R1")])[0] == "mismatch"
    assert scorer._pair_decision(40.0, 50.0, 2.0, covered(1))[0] == "partial"


def test_low_score_is_not_the_only_rejection_rule():
    # A direct covered requirement can make a low aggregate a partial fit.
    assert scorer._pair_decision(23.0, 45.0, 2.0, covered(1))[0] == "partial"
    # Conversely, diffuse similarity without evidence remains a mismatch.
    assert scorer._pair_decision(30.0, 30.0, 0.0, [Match(req_id="R1")])[0] == "mismatch"
