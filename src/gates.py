import shlex

from src.models import (
    Plan, CodeOutput, TestSuiteResult,
    DocOutput, GateResult,
)


def gate_plan_review(plan: Plan) -> GateResult:
    issues = []

    if not plan.tasks:
        issues.append("Plan has no tasks")

    if len(plan.milestones) < 1:
        issues.append("Plan has no milestones")

    tasks_set = set(plan.tasks)
    for task, deps in plan.dependencies.items():
        if task not in tasks_set:
            issues.append(f"Dependency references unknown task: {task}")
        for dep in deps:
            if dep not in tasks_set:
                issues.append(f"Dependency references unknown task: {dep}")

    edges = {}
    for task, deps in plan.dependencies.items():
        for dep in deps:
            edges.setdefault(task, set()).add(dep)

    visited = set()
    path = set()

    def has_cycle(node):
        if node in path:
            return True
        if node in visited:
            return False
        path.add(node)
        for dep in edges.get(node, set()):
            if has_cycle(dep):
                return True
        path.remove(node)
        visited.add(node)
        return False

    for task in plan.tasks:
        if has_cycle(task):
            issues.append(f"Circular dependency detected involving task: {task}")
            break

    passed = len(issues) == 0
    return GateResult(
        passed=passed,
        issues=issues,
        severity="blocking" if not passed else "warning",
    )


def _cmd_exit_code(result) -> int:
    return getattr(result, "exit_code", 0) if result else -1


def gate_static_analysis(backend) -> GateResult:
    if not backend:
        return GateResult(
            passed=True,
            issues=["No sandbox available, skipping static analysis"],
            severity="warning",
        )
    issues = []
    try:
        ruff_result = backend.execute("ruff check . 2>&1 || true")
        if _cmd_exit_code(ruff_result) != 0:
            issues.append(f"ruff check failed (exit code {_cmd_exit_code(ruff_result)})")
    except Exception as e:
        issues.append(f"ruff check failed: {e}")

    try:
        mypy_result = backend.execute("mypy . 2>&1 || true")
        if _cmd_exit_code(mypy_result) != 0:
            issues.append(f"mypy check failed (exit code {_cmd_exit_code(mypy_result)})")
    except Exception as e:
        issues.append(f"mypy check failed: {e}")

    passed = len(issues) == 0
    return GateResult(passed=passed, issues=issues, severity="blocking" if not passed else "warning")


def gate_sandbox_verification(backend, code_output: CodeOutput) -> GateResult:
    if not backend:
        return GateResult(passed=True, issues=["No sandbox, skipping"], severity="warning")
    issues = []
    for fc in code_output.files_created:
        try:
            result = backend.execute(f"test -f {shlex.quote(fc.path)} && echo 'EXISTS' || echo 'MISSING'")
            output = result.output.strip() if hasattr(result, "output") else ""
            if "MISSING" in output:
                issues.append(f"Expected file not found: {fc.path}")
        except Exception as e:
            issues.append(f"Could not verify {fc.path}: {e}")

    for dep in code_output.dependencies_installed:
        try:
            pkg = dep.split("==")[0]
            import_result = backend.execute(f"python -c 'import {shlex.quote(pkg)}' 2>&1")
            output = import_result.output.strip() if hasattr(import_result, "output") else ""
            if output and "error" in output.lower():
                issues.append(f"Dependency import failed: {dep}")
        except Exception:
            issues.append(f"Could not verify dependency: {dep}")

    passed = len(issues) == 0
    return GateResult(passed=passed, issues=issues, severity="blocking" if not passed else "warning")


def gate_coverage_minimum(test_result: TestSuiteResult, threshold: float = 80.0) -> GateResult:
    issues = []
    if test_result.coverage_pct is None:
        issues.append("Skipping coverage check: no coverage data (run with --cov)")
        return GateResult(passed=True, issues=issues, severity="warning")

    if test_result.coverage_pct < threshold:
        issues.append(
            f"Coverage {test_result.coverage_pct:.1f}% is below threshold {threshold:.0f}%"
        )
        return GateResult(passed=False, issues=issues, severity="blocking")

    return GateResult(passed=True, issues=issues, severity="warning")


def gate_regression_check(
    current: TestSuiteResult,
    history: list[TestSuiteResult],
) -> GateResult:
    issues = []
    if len(history) < 1:
        issues.append("Insufficient history for regression check (first iteration)")
        return GateResult(passed=True, issues=issues, severity="warning")

    previous = history[-1]
    new_failures = []
    for err in current.errors:
        if err not in previous.errors:
            new_failures.append(err)

    if new_failures:
        issues.append(f"Regression detected: {len(new_failures)} new failure(s)")
        for nf in new_failures[:3]:
            issues.append(f"  New failure: {nf[:100]}")

    return GateResult(
        passed=len(new_failures) == 0,
        issues=issues,
        severity="warning",
    )


def gate_plan_traceability(plan: Plan, code_output: CodeOutput) -> GateResult:
    issues = []
    all_files = [fc.path for fc in code_output.files_created + code_output.files_modified]

    for task in plan.tasks:
        task_lower = task.lower()
        matched = any(task_lower in file.lower() or file.lower() in task_lower for file in all_files)
        if not matched:
            issues.append(f"No file found matching task: {task}")

    passed = len(issues) == 0
    return GateResult(passed=passed, issues=issues, severity="blocking" if not passed else "warning")


def gate_doc_completeness(doc_output: DocOutput) -> GateResult:
    issues = []
    required = ["README.md", "docs/architecture.md"]
    created = set(doc_output.files_created)

    for req in required:
        if req not in created:
            issues.append(f"Required documentation file missing: {req}")

    passed = len(issues) == 0
    return GateResult(passed=passed, issues=issues, severity="blocking" if not passed else "warning")
