# AI Software Engineer

Build autonomous AI agents with **LangChain**, **Deep Agents**, and **E2B Sandboxes**.

This project is a reference implementation of a multi-agent system that takes a natural language software request and autonomously plans, codes, tests, debugs, and documents it — entirely within an isolated cloud sandbox. It serves as both a practical tool and a blueprint for building your own agentic AI workflows.

## How It Works

Three technologies work together:

**LangChain** provides the LLM abstraction layer. The coordinator and all sub-agents use `ChatOpenRouter` (via `langchain-openrouter`) as their language model, with LangChain's message primitives (`AIMessage`, `HumanMessage`, `ToolMessage`) as the universal communication format across the agent pipeline.

**Deep Agents** (`deepagents`) is the orchestration framework. A single coordinator agent, built with `create_deep_agent()`, manages five specialized sub-agents. Each sub-agent gets its own system prompt, tool access, and structured output format. The coordinator delegates work via `task()` calls and orchestrates the plan-code-test-review-document loop:

```
User Request
     │
     ▼
┌────────────────┐     ┌──────────────────┐
│  Coordinator   │────▶│     Planner      │──▶ Structured plan
│  (deep agent)  │     └──────────────────┘
│                │
│  Sub-agents:   │──▶ ┌──────────┐
│  • planner     │    │   Coder   │──▶ Write files, install deps
│  • coder       │    └──────────┘
│  • tester      │
│  • reviewer    │──▶ ┌──────────┐
│  • documenter  │    │  Tester   │──▶ pytest suite
│                │    └──────────┘
└────────────────┘
       │              ┌──────────┐
       │◀─────────────│ Reviewer │◀── Retry on failure
       │              └──────────┘
       │
       └──▶ ┌────────────┐
            │ Documenter │──▶ README + architecture docs
            └────────────┘
```

**E2B Sandboxes** provide the secure execution environment. The `managed_sandbox()` context manager creates an E2B cloud sandbox, wraps it in a `langchain_e2b.E2BSandbox` backend, and passes it to the deep agent. All file writes, shell commands, and test runs happen inside this sandbox — no code touches the host machine.

## Architecture

```
ai-software-engineer/
├── main.py                      # CLI entry point — wires everything together
│
├── src/
│   ├── config.py               # Settings dataclass, env loading via python-dotenv
│   ├── models.py               # Pydantic models (Plan, FileChange)
│   ├── sandbox.py              # managed_sandbox() — E2B lifecycle as context manager
│   ├── prompts.py              # 6 system prompts for coordinator + 5 sub-agents
│   ├── coordinator.py          # build_coordinator() — create_deep_agent factory
│   └── display.py              # Rich terminal UI rendering
│
├── tests/
│   └── test_imports.py         # Smoke test
│
├── pyproject.toml              # Dependencies
├── uv.lock                     # Locked package versions
└── .env                        # API keys
```

### Agent Pipeline

The `build_coordinator()` factory in `src/coordinator.py` assembles the system:

```python
agent = create_deep_agent(
    model=model,                       # ChatOpenRouter instance
    system_prompt=COORDINATOR_PROMPT,  # Orchestration logic
    subagents=[
        planner_subagent,              # Outputs Plan (Pydantic model)
        coder_subagent,                # File system + shell access
        tester_subagent,               # pytest generation and execution
        reviewer_subagent,             # Bug/hallucination detection
        documenter_subagent,           # README + architecture docs
    ],
    backend=backend,                   # E2BSandbox instance
    name="ai-software-engineer",
)
```

Each sub-agent is a configuration dictionary with a `name`, `description`, `system_prompt`, and optional `response_format` for structured output. The coordinator uses `task()` calls to delegate, passing full context so sub-agents work independently.

The planner returns a Pydantic `Plan` model:

```python
class Plan(BaseModel):
    objective: str
    tasks: list[str]
    dependencies: dict[str, list[str]]
    milestones: list[str]
```

### Sandbox Lifecycle

The `managed_sandbox()` context manager in `src/sandbox.py` handles the E2B lifecycle:

```python
@contextmanager
def managed_sandbox(settings: Settings) -> Iterator[E2BSandbox]:
    e2b_sandbox = Sandbox.create(timeout=settings.sandbox_timeout)
    backend = E2BSandbox(sandbox=e2b_sandbox)
    try:
        yield backend
    finally:
        e2b_sandbox.kill()
```

The sandbox wraps E2B's SDK in a `langchain_e2b.E2BSandbox` backend, making it compatible with the deep agents runtime while providing file system and shell execution capabilities.

## Workflow

For every user request, the coordinator executes this loop:

1. **Plan** — delegate to planner; returns a Plan with tasks, dependencies, milestones
2. **Code** — for each task, delegate to coder; files are written in the sandbox
3. **Test** — delegate to tester; writes pytest tests and runs the suite
4. **Review** — if tests fail, delegate to reviewer; returns concrete fix suggestions
5. **Fix** — delegate to coder with fix suggestions
6. **Repeat** — steps 3–5 until all tests pass or max iterations hit
7. **Document** — delegate to documenter for README.md and docs/architecture.md

## Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) — Python package manager
- [E2B](https://e2b.dev) API key — for cloud sandbox execution
- OpenRouter API key — LLM access

## Setup

```bash
git clone <repo-url>
cd ai-software-engineer
uv sync
```

Copy `.env.example` to `.env` and add your keys:

| Variable | Required | Default | Description |
|---|---|---|---|
| `E2B_API_KEY` | Yes | — | E2B sandbox API key |
| `OPENROUTER_API_KEY` | Yes | — | OpenRouter API key |
| `AGENT_MODEL` | No | `openrouter/owl-alpha` | LLM model to use |

## Usage

```bash
uv run python main.py 'Build a CLI todo app with SQLite'
uv run python main.py 'Create a FastAPI REST API for a blog'
uv run python main.py 'Build a web scraper that outputs CSV reports'
```

The Rich terminal display streams progress — phase labels, tool calls, file operations, and test results — in real time.

## Dependencies

| Package | Role |
|---|---|
| `deepagents>=0.6.12` | Multi-agent orchestration via `create_deep_agent()` |
| `langchain>=1.3.11` | LLM abstraction, message types, tool calling |
| `langchain-openrouter>=0.2.4` | OpenRouter LLM provider for LangChain |
| `langchain-e2b>=0.0.4` | E2B sandbox as a LangChain backend |
| `e2b>=2.30.0` | Cloud sandbox creation and lifecycle |
| `rich>=15.0.0` | Terminal UI rendering |
| `python-dotenv>=1.0.1` | `.env` file loading |
| `pytest>=9.1.1` | Testing (dev) |

## Development

```bash
uv run pytest tests/ -v        # Run tests
uv pip install -e .            # Editable install
```

## License

MIT
