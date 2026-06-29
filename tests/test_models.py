import pytest
from pydantic import ValidationError
from src.models import (
    CodeOutput, FileChange, TestSuiteResult,
    ReviewIssue, ReviewFindings, DocOutput,
    GateResult, PipelineResult, Plan,
)


class TestCodeOutput:
    def test_empty_code_output(self):
        output = CodeOutput()
        assert output.files_created == []
        assert output.files_modified == []
        assert output.summary == ""
        assert output.dependencies_installed == []

    def test_code_output_with_file_changes(self):
        fc = FileChange(path="src/main.py", action="create", description="Entry point")
        output = CodeOutput(
            files_created=[fc],
            summary="Created entry point",
            dependencies_installed=["click"],
        )
        assert len(output.files_created) == 1
        assert output.files_created[0].path == "src/main.py"


class TestTestSuiteResult:
    def test_all_pass(self):
        result = TestSuiteResult(passed=10, failed=0, coverage_pct=95.0)
        assert result.passed == 10
        assert result.failed == 0
        assert result.coverage_pct == 95.0

    def test_with_failures(self):
        result = TestSuiteResult(
            passed=8, failed=2,
            errors=["AssertionError: expected 5 got 4", "ValueError: invalid input"],
            tracebacks=["Traceback (most recent call last):...", "Traceback..."],
        )
        assert len(result.errors) == 2
        assert result.failed == 2


class TestReviewFindings:
    def test_review_issue_construction(self):
        issue = ReviewIssue(
            file="src/main.py",
            line=42,
            severity="error",
            description="Unhandled KeyError",
            root_cause="dict access without .get()",
            fix_suggestion="Change d[key] to d.get(key)",
        )
        assert issue.file == "src/main.py"
        assert issue.severity == "error"
        assert issue.fix_suggestion.startswith("Change")

    def test_empty_findings(self):
        findings = ReviewFindings(
            issues=[], summary="No issues found", should_fix=False
        )
        assert len(findings.issues) == 0
        assert findings.should_fix is False


class TestDocOutput:
    def test_doc_output(self):
        doc = DocOutput(
            files_created=["README.md", "docs/architecture.md"],
            summary="Generated project documentation",
        )
        assert len(doc.files_created) == 2


class TestGateResult:
    def test_gate_passed(self):
        gate = GateResult(passed=True, issues=[], severity="blocking")
        assert gate.passed is True
        assert gate.severity == "blocking"

    def test_gate_failed_with_issues(self):
        gate = GateResult(
            passed=False,
            issues=["ruff: E501 line too long", "mypy: incompatible type"],
            severity="blocking",
        )
        assert gate.passed is False
        assert len(gate.issues) == 2


class TestPipelineResult:
    def test_default_state(self):
        result = PipelineResult()
        assert result.status == "unknown"
        assert result.test_results == []
        assert result.iterations_used == 0

    def test_full_result(self):
        plan = Plan(
            objective="Build CLI todo app",
            tasks=["Create main.py", "Add SQLite storage"],
            dependencies={"Add SQLite storage": ["Create main.py"]},
            milestones=["MVP with add/list/complete"],
        )
        result = PipelineResult(
            status="completed",
            plan=plan,
            iterations_used=3,
            elapsed_seconds=45.2,
        )
        assert result.status == "completed"
        assert result.plan.objective == "Build CLI todo app"
