"""Integration-level tests that verify pipeline components work together.
These tests mock the E2B sandbox and deep_agent to avoid real API calls."""

from unittest.mock import MagicMock, patch
from src.config import Settings
from src.pipeline import WorkflowPipeline
from src.gates import (
    gate_plan_review,
    gate_coverage_minimum,
    gate_plan_traceability,
    gate_doc_completeness,
)
from src.models import (
    Plan, CodeOutput, FileChange,
    TestSuiteResult, DocOutput,
)


def test_settings_has_max_iterations():
    settings = Settings()
    assert settings.max_iterations == 10


def test_gate_plan_review_good_plan():
    plan = Plan(
        objective="Build CLI app",
        tasks=["Create src/main.py", "Create src/db.py"],
        dependencies={"Create src/db.py": ["Create src/main.py"]},
        milestones=["MVP"],
    )
    result = gate_plan_review(plan)
    assert result.passed is True


def test_gate_coverage_below_threshold():
    result = TestSuiteResult(passed=5, failed=0, coverage_pct=45.0)
    gate = gate_coverage_minimum(result, threshold=80.0)
    assert gate.passed is False


def test_gate_traceability_mismatch():
    plan = Plan(
        objective="Test",
        tasks=["Create main.py", "Create utils.py"],
        dependencies={},
        milestones=[],
    )
    code = CodeOutput(
        files_created=[FileChange(path="main.py", action="create", description="")],
    )
    result = gate_plan_traceability(plan, code)
    assert result.passed is False


def test_gate_doc_completeness_missing_arch():
    doc = DocOutput(files_created=["README.md"])
    result = gate_doc_completeness(doc)
    assert result.passed is False


@patch("src.pipeline.build_coordinator")
def test_pipeline_creates_agent(mock_build):
    mock_agent = MagicMock()
    mock_agent.stream.return_value = []
    mock_build.return_value = mock_agent

    settings = Settings()
    pipeline = WorkflowPipeline(settings, backend=None)
    assert pipeline.agent is not None
    assert pipeline.state.status == "unknown"
