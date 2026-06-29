from __future__ import annotations

from typing import Any

from deepagents import create_deep_agent
from langchain_openrouter import ChatOpenRouter

from src.config import Settings
from src.models import Plan, CodeOutput, TestSuiteResult, ReviewFindings, DocOutput
from src.prompts import (
    COORDINATOR_PROMPT,
    PLANNER_PROMPT,
    CODER_PROMPT,
    TESTER_PROMPT,
    REVIEWER_PROMPT,
    DOCUMENTER_PROMPT,
)


def build_coordinator(
    settings: Settings,
    backend: Any = None,
):
    model = ChatOpenRouter(model=settings.model)

    planner_subagent = {
        "name": "planner",
        "description": (
            "Analyzes requirements and creates an implementation plan "
            "with tasks, dependencies, and milestones."
        ),
        "system_prompt": PLANNER_PROMPT,
        "response_format": Plan,
    }

    coder_subagent = {
        "name": "coder",
        "description": (
            "Writes and edits source code files in the sandbox filesystem. "
            "Installs dependencies and validates code compiles."
        ),
        "system_prompt": CODER_PROMPT,
        "response_format": CodeOutput,
    }

    tester_subagent = {
        "name": "tester",
        "description": (
            "Writes pytest tests, runs the test suite, and returns "
            "pass/fail results with full error output."
        ),
        "system_prompt": TESTER_PROMPT,
        "response_format": TestSuiteResult,
    }

    reviewer_subagent = {
        "name": "reviewer",
        "description": (
            "Reviews code quality, test failures, and execution errors. "
            "Detects hallucinations and produces concrete fix suggestions."
        ),
        "system_prompt": REVIEWER_PROMPT,
        "response_format": ReviewFindings,
    }

    documenter_subagent = {
        "name": "documenter",
        "description": (
            "Creates README.md, architecture docs, and API documentation "
            "for a completed project."
        ),
        "system_prompt": DOCUMENTER_PROMPT,
        "response_format": DocOutput,
    }

    agent = create_deep_agent(
        model=model,
        system_prompt=COORDINATOR_PROMPT,
        subagents=[
            planner_subagent,
            coder_subagent,
            tester_subagent,
            reviewer_subagent,
            documenter_subagent,
        ],
        backend=backend,
        name="ai-software-engineer",
    )

    return agent
