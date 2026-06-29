from src.models import (
    Plan, FileChange, CodeOutput,
    TestSuiteResult, DocOutput,
)
from src.gates import (
    gate_plan_review,
    gate_coverage_minimum,
    gate_regression_check,
    gate_static_analysis,
    gate_sandbox_verification,
    gate_plan_traceability,
    gate_doc_completeness,
)


class TestGatePlanReview:
    def test_valid_plan_passes(self):
        plan = Plan(
            objective="Build CLI",
            tasks=["Create main.py", "Add storage.py"],
            dependencies={"Add storage.py": ["Create main.py"]},
            milestones=["Working CLI"],
        )
        result = gate_plan_review(plan)
        assert result.passed is True

    def test_plan_with_circular_deps_fails(self):
        plan = Plan(
            objective="Circular",
            tasks=["Task A", "Task B"],
            dependencies={"Task A": ["Task B"], "Task B": ["Task A"]},
            milestones=["Done"],
        )
        result = gate_plan_review(plan)
        assert result.passed is False
        assert any("circular" in issue.lower() for issue in result.issues)

    def test_plan_with_no_tasks_fails(self):
        plan = Plan(objective="Empty", tasks=[], dependencies={}, milestones=[])
        result = gate_plan_review(plan)
        assert result.passed is False


class TestGateCoverage:
    def test_above_threshold_passes(self):
        result = TestSuiteResult(passed=10, failed=0, coverage_pct=85.0)
        gate = gate_coverage_minimum(result, threshold=80.0)
        assert gate.passed is True

    def test_below_threshold_fails(self):
        result = TestSuiteResult(passed=10, failed=0, coverage_pct=50.0)
        gate = gate_coverage_minimum(result, threshold=80.0)
        assert gate.passed is False

    def test_no_coverage_data_skips(self):
        result = TestSuiteResult(passed=10, failed=0, coverage_pct=None)
        gate = gate_coverage_minimum(result, threshold=80.0)
        assert gate.passed is True
        assert any("skip" in issue.lower() for issue in gate.issues)


class TestGateRegression:
    def test_no_regression(self):
        old = TestSuiteResult(passed=10, failed=0, errors=[])
        current = TestSuiteResult(passed=9, failed=1)
        gate = gate_regression_check(current, [old])
        assert gate.passed is True

    def test_insufficient_history_warns(self):
        current = TestSuiteResult(passed=9, failed=1)
        gate = gate_regression_check(current, [])
        assert gate.passed is True
        assert any("insufficient" in issue.lower() for issue in gate.issues)

    def test_new_failure_detected(self):
        old = TestSuiteResult(passed=10, failed=1, errors=["old error"])
        current = TestSuiteResult(
            passed=9, failed=2,
            errors=["old error", "new error"],
        )
        gate = gate_regression_check(current, [old])
        assert len([i for i in gate.issues if "Regression" in i]) > 0


class FakeBackend:
    def execute(self, cmd):
        return type("Result", (), {"output": "", "exit_code": 0})()


class TestGateStaticAnalysis:
    def test_no_backend_skips(self):
        result = gate_static_analysis(None)
        assert result.passed is True
        assert any("No sandbox" in i for i in result.issues)

    def test_with_backend_passes(self):
        result = gate_static_analysis(FakeBackend())
        assert result.passed is True


class TestGateSandboxVerification:
    def test_no_backend_skips(self):
        code = CodeOutput()
        result = gate_sandbox_verification(None, code)
        assert result.passed is True

    def test_with_empty_code_passes(self):
        code = CodeOutput()
        result = gate_sandbox_verification(FakeBackend(), code)
        assert result.passed is True


class TestGatePlanTraceability:
    def test_all_tasks_traced(self):
        plan = Plan(
            objective="Test",
            tasks=["Create main.py", "Add utils.py"],
            dependencies={},
            milestones=[],
        )
        code = CodeOutput(
            files_created=[
                FileChange(path="main.py", action="create", description=""),
                FileChange(path="utils.py", action="create", description=""),
            ],
        )
        result = gate_plan_traceability(plan, code)
        assert result.passed is True

    def test_untraced_task_fails(self):
        plan = Plan(
            objective="Test",
            tasks=["Create main.py", "Add database.py"],
            dependencies={},
            milestones=[],
        )
        code = CodeOutput(
            files_created=[
                FileChange(path="main.py", action="create", description=""),
            ],
        )
        result = gate_plan_traceability(plan, code)
        assert result.passed is False
        assert any("database" in issue.lower() for issue in result.issues)


class TestGateDocCompleteness:
    def test_missing_doc_files_fails(self):
        doc = DocOutput(files_created=["README.md"])
        result = gate_doc_completeness(doc)
        assert result.passed is False

    def test_all_doc_files_present_passes(self):
        doc = DocOutput(files_created=["README.md", "docs/architecture.md"])
        result = gate_doc_completeness(doc)
        assert result.passed is True
