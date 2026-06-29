import pytest
from unittest.mock import MagicMock, patch
from src.models import (
    Plan, CodeOutput, FileChange,
    TestSuiteResult, ReviewFindings, ReviewIssue,
    DocOutput, PipelineResult,
)
from src.pipeline import WorkflowPipeline


class FakeSettings:
    max_iterations = 5
    model = "openrouter/owl-alpha"


class FakeBackend:
    def execute(self, cmd):
        return type("Result", (), {"output": "", "exit_code": 0})()


@pytest.fixture
def pipeline():
    settings = FakeSettings()
    backend = FakeBackend()
    with patch("src.pipeline.build_coordinator") as mock_build:
        mock_agent = MagicMock()
        mock_agent.stream.return_value = []
        mock_build.return_value = mock_agent
        pl = WorkflowPipeline(settings, backend)
        return pl


class TestPipelineInitialization:
    def test_creates_agent(self, pipeline):
        assert pipeline.agent is not None
        assert pipeline.settings.max_iterations == 5
        assert pipeline.state.status == "unknown"
        assert pipeline.iteration_count == 0

    def test_events_start_empty(self, pipeline):
        assert pipeline.event_handlers["phase_start"] == []
        assert pipeline.event_handlers["gate_result"] == []


class TestPipelineEventSystem:
    def test_on_registers_handler(self, pipeline):
        calls = []
        pipeline.on("phase_start", lambda d: calls.append(d))
        assert len(pipeline.event_handlers["phase_start"]) == 1

    def test_emit_calls_handlers(self, pipeline):
        calls = []
        pipeline.on("phase_start", lambda d: calls.append(d))
        pipeline._emit("phase_start", {"phase": "test"})
        assert len(calls) == 1
        assert calls[0]["phase"] == "test"


class TestPipelineLoopControl:
    def test_max_iterations_respected(self, pipeline):
        pipeline._phase_test = MagicMock(
            side_effect=[
                TestSuiteResult(passed=0, failed=3),
                TestSuiteResult(passed=0, failed=2),
                TestSuiteResult(passed=0, failed=1),
                TestSuiteResult(passed=5, failed=0),
            ]
        )
        pipeline._phase_review = MagicMock(
            return_value=ReviewFindings(issues=[], summary="fix", should_fix=True)
        )
        pipeline._phase_fix = MagicMock(
            return_value=CodeOutput(
                files_created=[FileChange(path="fix.py", action="create", description="fix")],
            )
        )
        pipeline.state.plan = Plan(
            objective="fix",
            tasks=["fix"],
            dependencies={},
            milestones=["done"],
        )

        result = pipeline._run_loop()
        assert result.status == "completed"
        assert result.iterations_used == 3
        assert pipeline.iteration_count == 3

    def test_escalates_on_max_iterations(self, pipeline):
        pipeline.settings.max_iterations = 2
        pipeline._phase_test = MagicMock(
            side_effect=[
                TestSuiteResult(passed=0, failed=3, errors=["err1"]),
                TestSuiteResult(passed=0, failed=3, errors=["err1"]),
            ]
        )
        pipeline._phase_review = MagicMock(
            return_value=ReviewFindings(issues=[], summary="fix", should_fix=True)
        )
        pipeline._phase_fix = MagicMock(
            return_value=CodeOutput(
                files_created=[FileChange(path="fix.py", action="create", description="fix")],
            )
        )
        pipeline.state.plan = Plan(
            objective="fix",
            tasks=["fix"],
            dependencies={},
            milestones=["done"],
        )

        result = pipeline._run_loop()
        assert result.status == "escalated"
        assert result.iterations_used == 2
        assert "max iterations" in (result.error or "").lower()

    def test_escalates_on_review_should_fix_false(self, pipeline):
        pipeline._phase_test = MagicMock(
            return_value=TestSuiteResult(passed=0, failed=1)
        )
        pipeline._phase_review = MagicMock(
            return_value=ReviewFindings(issues=[], summary="unfixable", should_fix=False)
        )

        result = pipeline._run_loop()
        assert result.status == "escalated"
        assert "unfixable" in (result.error or "").lower()


class TestPipelineFullRun:
    def test_run_completes_flow(self, pipeline):
        with (
            patch.object(pipeline, "_phase_plan") as mock_plan,
            patch.object(pipeline, "_gate_plan_review") as mock_gate_plan,
            patch.object(pipeline, "_phase_code") as mock_code,
            patch.object(pipeline, "_run_loop") as mock_loop,
            patch.object(pipeline, "_phase_document") as mock_doc,
            patch.object(pipeline, "_gate_doc_completeness") as mock_gate_doc,
        ):
            plan = Plan(
                objective="Test",
                tasks=["Create main.py"],
                dependencies={},
                milestones=["MVP"],
            )
            mock_plan.return_value = plan
            mock_code.return_value = CodeOutput()
            mock_loop.return_value = PipelineResult(
                status="completed", iterations_used=1,
                test_results=[TestSuiteResult(passed=5, failed=0)],
            )
            mock_doc.return_value = DocOutput(
                files_created=["README.md", "docs/architecture.md"],
            )

            result = pipeline.run("Build a CLI app")
            assert result.status == "completed"
            mock_plan.assert_called_once()
            mock_code.assert_called_once()
            mock_loop.assert_called_once()
            mock_doc.assert_called_once()
            mock_gate_doc.assert_called_once()

    def test_run_escalated_skips_document(self, pipeline):
        with (
            patch.object(pipeline, "_phase_plan") as mock_plan,
            patch.object(pipeline, "_gate_plan_review") as mock_gate_plan,
            patch.object(pipeline, "_phase_code") as mock_code,
            patch.object(pipeline, "_run_loop") as mock_loop,
            patch.object(pipeline, "_phase_document") as mock_doc,
        ):
            plan = Plan(
                objective="Test",
                tasks=["Create main.py"],
                dependencies={},
                milestones=["MVP"],
            )
            mock_plan.return_value = plan
            mock_code.return_value = CodeOutput()
            mock_loop.return_value = PipelineResult(
                status="escalated", error="Something went wrong",
            )

            result = pipeline.run("Build a CLI app")
            assert result.status == "escalated"
            mock_doc.assert_not_called()
