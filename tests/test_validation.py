"""Regression tests for the retired resume-claim validation gates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from validation import ladder  # noqa: E402


def test_generated_claims_are_not_rejected_by_retired_validator():
    generated = "Led a Kubernetes migration on AWS, improving throughput by 60%"
    violations = ladder.validate(
        generated,
        "Assisted with Python data cleanup",
        {"python"},
    )
    assert violations == []


def test_unsupported_claim_rate_no_longer_reports_claim_warnings():
    generated = [
        "Built a Kubernetes platform serving 500 users",
        "Led a team of 12 engineers to improve latency by 40%",
    ]
    assert ladder.unsupported_claim_rate(generated, {"python"}) == 0.0
