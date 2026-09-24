import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
from llm_resume_structure_integration import validate_raw_response


def statuses(raw):
    return {metric.name: metric.passed for metric in validate_raw_response(raw)}


def test_valid_raw_response_passes_every_architectural_metric():
    raw = """# Jordan Lee
## Selected Projects
### Project 1 - Knowledge Assistant
Technologies: LangChain, FastAPI
- Built a retrieval service.
### Project 2 - Service Platform
Technologies: FastAPI, Docker
- Built a workflow API.
"""
    assert all(statuses(raw).values())


def test_collapsed_projects_filler_and_artifacts_fail():
    raw = """Sure, here is your resume:
```markdown
- Project 1 and Project 2: Built with LangChain and FastAPI
<think>reasoning</think>
```
"""
    result = statuses(raw)
    assert not result["No Conversational Filler"]
    assert not result["Structural Integrity"]
    assert result["Metadata Retention"]
    assert not result["Clean Artifacts"]
