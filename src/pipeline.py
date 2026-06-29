import time
import json
from typing import Any, Callable

from src.config import Settings
from src.coordinator import build_coordinator
from src.models import (
    Plan, CodeOutput, FileChange,
    TestSuiteResult, ReviewFindings, ReviewIssue,
    DocOutput, GateResult, PipelineResult,
)
from src.gates import (
    gate_plan_review,
    gate_static_analysis,
    gate_sandbox_verification,
    gate_coverage_minimum,
    gate_regression_check,
    gate_plan_traceability,
    gate_doc_completeness,
)


class WorkflowPipeline:
    def __init__(self, settings: Settings, backend: Any = None):
        self.settings = settings
        self.backend = backend
        self.agent = build_coordinator(settings, backend=backend)
        self.state = PipelineResult()
        self.iteration_count = 0
        self.event_handlers: dict[str, list[Callable]] = {
            "phase_start": [],
            "phase_output": [],
            "gate_result": [],
            "pipeline_complete": [],
            "stream_chunk": [],
        }

    def on(self, event: str, callback: Callable) -> None:
        self.event_handlers.setdefault(event, []).append(callback)

    def _emit(self, event: str, data: Any) -> None:
        for cb in self.event_handlers.get(event, []):
            cb(data)

    def _invoke_agent(self, prompt: str) -> dict:
        full_messages = []
        for chunk in self.agent.stream(
            {"messages": [{"role": "user", "content": prompt}]},
            stream_mode="updates",
            version="v2",
        ):
            self._emit("stream_chunk", chunk)
            if chunk.get("type") != "updates":
                continue
            data = chunk.get("data")
            if data is None:
                continue
            for node_name, node_data in data.items():
                if node_data is None:
                    continue
                messages = node_data.get("messages")
                if messages:
                    full_messages.extend(messages)

        for msg in reversed(full_messages):
            if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
                try:
                    return json.loads(msg.content)
                except (json.JSONDecodeError, TypeError):
                    return {"raw": msg.content}
        return {}

    def _phase_plan(self, request: str) -> Plan:
        self._emit("phase_start", {"phase": "plan", "label": "Planning", "color": "magenta"})
        data = self._invoke_agent(
            f"Execute the planner phase for this request: {request}\n\n"
            "Return valid JSON matching the Plan schema."
        )
        plan = Plan(**data)
        self.state.plan = plan
        self._emit("phase_output", {"phase": "plan", "output": plan})
        return plan

    def _phase_code(self, plan: Plan) -> CodeOutput:
        self._emit("phase_start", {"phase": "code", "label": "Coding", "color": "cyan"})
        plan_json = plan.model_dump_json()
        data = self._invoke_agent(
            f"Execute the coder phase.\n\nPlan:\n{plan_json}\n\n"
            "Return valid JSON matching the CodeOutput schema."
        )
        code = CodeOutput(**data)
        self.state.code = code
        self._emit("phase_output", {"phase": "code", "output": code})
        return code

    def _phase_test(self) -> TestSuiteResult:
        self._emit("phase_start", {"phase": "test", "label": "Testing", "color": "yellow"})
        context = ""
        if self.state.code:
            context = self.state.code.model_dump_json()
        data = self._invoke_agent(
            f"Execute the tester phase.\n\n"
            f"Code context:\n{context}\n\n"
            "Return valid JSON matching the TestSuiteResult schema."
        )
        test_result = TestSuiteResult(**data)
        self.state.test_results.append(test_result)
        self._emit("phase_output", {"phase": "test", "output": test_result})
        return test_result

    def _phase_review(self, test_result: TestSuiteResult) -> ReviewFindings:
        self._emit("phase_start", {"phase": "review", "label": "Reviewing", "color": "red"})
        data = self._invoke_agent(
            f"Execute the reviewer phase.\n\nTest results:\n{test_result.model_dump_json()}\n\n"
            "Return valid JSON matching the ReviewFindings schema."
        )
        review = ReviewFindings(**data)
        self.state.review = review
        self._emit("phase_output", {"phase": "review", "output": review})
        return review

    def _phase_fix(self, review: ReviewFindings) -> CodeOutput:
        self._emit("phase_start", {"phase": "fix", "label": "Fixing", "color": "cyan"})
        review_json = review.model_dump_json()
        data = self._invoke_agent(
            f"Execute the coder phase to apply these fixes.\n\n"
            f"Review findings:\n{review_json}\n\n"
            "Return valid JSON matching the CodeOutput schema."
        )
        code = CodeOutput(**data)
        self._emit("phase_output", {"phase": "fix", "output": code})
        return code

    def _phase_document(self) -> DocOutput:
        self._emit("phase_start", {"phase": "document", "label": "Documentation", "color": "green"})
        data = self._invoke_agent(
            "Execute the documenter phase.\n\n"
            "Return valid JSON matching the DocOutput schema."
        )
        doc = DocOutput(**data)
        self.state.doc = doc
        self._emit("phase_output", {"phase": "document", "output": doc})
        return doc

    def _evaluate_gate(self, name: str, gate_result: GateResult) -> None:
        self._emit("gate_result", {"gate": name, "result": gate_result})
        if not gate_result.passed and gate_result.severity == "blocking":
            raise RuntimeError(
                f"Gate '{name}' blocked: {'; '.join(gate_result.issues)}"
            )

    def _gate_plan_review(self, plan: Plan) -> None:
        result = gate_plan_review(plan)
        self._evaluate_gate("plan_review", result)

    def _gate_static_analysis(self) -> None:
        result = gate_static_analysis(self.backend)
        self._evaluate_gate("static_analysis", result)

    def _gate_sandbox_verification(self, code: CodeOutput) -> None:
        result = gate_sandbox_verification(self.backend, code)
        self._evaluate_gate("sandbox_verification", result)

    def _gate_coverage(self, test_result: TestSuiteResult) -> None:
        result = gate_coverage_minimum(test_result)
        self._evaluate_gate("coverage_minimum", result)

    def _gate_regression(self, test_result: TestSuiteResult) -> None:
        result = gate_regression_check(test_result, self.state.test_results[:-1])
        self._evaluate_gate("regression_check", result)

    def _gate_plan_traceability(self, plan: Plan, code: CodeOutput) -> None:
        result = gate_plan_traceability(plan, code)
        self._evaluate_gate("plan_traceability", result)

    def _gate_doc_completeness(self, doc: DocOutput) -> None:
        result = gate_doc_completeness(doc)
        self._evaluate_gate("doc_completeness", result)

    def _run_loop(self) -> PipelineResult:
        while self.iteration_count < self.settings.max_iterations:
            test_result = self._phase_test()
            self._gate_coverage(test_result)

            if test_result.failed == 0:
                self.state.status = "completed"
                self.state.iterations_used = self.iteration_count
                return self.state

            if self.iteration_count >= self.settings.max_iterations - 1:
                self.state.status = "escalated"
                self.state.iterations_used = self.iteration_count + 1
                self.state.error = (
                    f"Max iterations ({self.settings.max_iterations}) reached "
                    f"with {test_result.failed} failing test(s)"
                )
                return self.state

            review = self._phase_review(test_result)
            self._gate_regression(test_result)

            if not review.should_fix:
                self.state.status = "escalated"
                self.state.iterations_used = self.iteration_count + 1
                self.state.error = f"Reviewer escalated: {review.summary}"
                return self.state

            fix_code = self._phase_fix(review)
            if self.state.plan is not None:
                self._gate_plan_traceability(self.state.plan, fix_code)
            self.iteration_count += 1

        self.state.status = "escalated"
        self.state.iterations_used = self.iteration_count
        self.state.error = "Exited loop without completing"
        return self.state

    def run(self, request: str) -> PipelineResult:
        start_time = time.time()
        self.state = PipelineResult()

        try:
            plan = self._phase_plan(request)
            self._gate_plan_review(plan)

            code = self._phase_code(plan)
            self._gate_static_analysis()
            self._gate_sandbox_verification(code)

            result = self._run_loop()

            if result.status == "completed":
                doc = self._phase_document()
                self._gate_doc_completeness(doc)

            self.state = result
        except RuntimeError as e:
            if self.state.status == "unknown":
                self.state.status = "failed"
            self.state.error = str(e)
        except Exception as e:
            self.state.status = "failed"
            self.state.error = f"Unexpected error: {e}"

        self.state.elapsed_seconds = time.time() - start_time
        self._emit("pipeline_complete", self.state)
        return self.state
