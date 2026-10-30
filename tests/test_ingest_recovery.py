import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

from pipeline.ingest import _recover_fact_text  # noqa: E402
from schemas import ExtractedFact, ExtractedFacts  # noqa: E402


def test_incomplete_fact_output_recovers_source_claims_and_entities():
    result = _recover_fact_text(
        ExtractedFacts(facts=[ExtractedFact(context="Platform", tech=["python"]),
                             ExtractedFact(text="Built the API", tech=["fastapi"])]),
        "### Engineer | Source Corp\n- Built the API\n- Validated Python integrations",
    )
    texts = [fact.text for fact in result.facts]
    assert "Built the API" in texts
    assert "Validated Python integrations" in texts
    assert result.facts[0].tech == ["python"]


def test_empty_fact_output_recovers_all_source_claims():
    result = _recover_fact_text(
        ExtractedFacts(),
        "- Designed the service\n- Deployed the release",
    )
    assert [fact.text for fact in result.facts] == [
        "Designed the service", "Deployed the release"
    ]
