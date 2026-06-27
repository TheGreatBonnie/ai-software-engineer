from __future__ import annotations

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.spinner import Spinner

PHASE_LABELS: dict[str, tuple[str, str, str]] = {
    "planner": ("📋", "Planning", "magenta"),
    "coder": ("💻", "Coding", "cyan"),
    "tester": ("🧪", "Testing", "yellow"),
    "reviewer": ("👁️", "Reviewing", "red"),
    "documenter": ("📝", "Documentation", "green"),
}

TOOL_ICONS: dict[str, str] = {
    "write_file": "📝",
    "read_file": "📖",
    "execute": "⚙️",
    "write_todos": "📋",
    "glob": "🔍",
    "grep": "🔍",
    "ls": "📂",
}

TODO_STATUS_ICONS = {
    "pending": "○",
    "in_progress": "◐",
    "completed": "✓",
}
TODO_STATUS_COLORS = {
    "pending": "white",
    "in_progress": "yellow",
    "completed": "green",
}


class AgentDisplay:
    def __init__(self, console: Console):
        self.console = console
        self.seen_ids: set[str] = set()
        self.current_phase = ""
        self.spinner = Spinner("dots", text="Starting...")

    def update_status(self, text: str) -> None:
        self.spinner = Spinner("dots", text=text)

    def _render_todos(self, todos: list[dict[str, Any]]) -> None:
        if not todos:
            self.console.print("  [bold white]📋 Planning[/]")
            self.console.print("  [dim]No todo items provided[/]")
            self.update_status("Planning...")
            return

        self.console.print("\n  [bold white]📋 Planning[/]")
        for todo in todos:
            if not isinstance(todo, dict):
                continue
            content = str(todo.get("content", "Untitled step")).strip() or "Untitled step"
            status = str(todo.get("status", "pending")).strip()
            icon = TODO_STATUS_ICONS.get(status, "•")
            color = TODO_STATUS_COLORS.get(status, "white")
            self.console.print(f"  [{color}]{icon} {content}[/]")

        active = next(
            (
                t.get("content", "")
                for t in todos
                if isinstance(t, dict) and t.get("status") == "in_progress"
            ),
            None,
        )
        if active:
            self.update_status(f"Planning: {active[:40]}...")

    def _render_content(self, content: str | list | Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for p in content:
                if isinstance(p, dict) and p.get("type") == "text":
                    parts.append(p.get("text", ""))
            return "\n".join(parts)
        return str(content) if content else ""

    def _has_tool_call(self, tool_calls: list[dict[str, Any]], name: str) -> bool:
        for tc in tool_calls:
            if tc.get("name") == name:
                return True
        for tc in tool_calls:
            if tc.get("name") == name:
                break
        return any(tc.get("name") == name for tc in tool_calls)

    def print_message(self, msg: Any) -> None:
        if msg.id and msg.id in self.seen_ids:
            return
        if msg.id:
            self.seen_ids.add(msg.id)

        if isinstance(msg, HumanMessage):
            return

        if isinstance(msg, AIMessage):
            content = self._render_content(msg.content)
            if content and content.strip():
                self.console.print(
                    Panel(Markdown(content), title="Coordinator", border_style="green")
                )

            if msg.tool_calls:
                self._render_tool_calls(msg.tool_calls)
            return

        if isinstance(msg, ToolMessage):
            name = getattr(msg, "name", "") or ""
            if name == "task":
                self.console.print("  [bold green]✓ Phase complete[/]")
                self.update_status("Coordinating...")
            elif name == "write_file":
                self.console.print("  [green]✓ File written[/]")
            elif name == "write_todos":
                self.console.print("  [green]✓ Plan updated[/]")
            elif name == "execute":
                code = (
                    msg.additional_kwargs.get("exit_code", 0)
                    if hasattr(msg, "additional_kwargs") and msg.additional_kwargs
                    else 0
                )
                color = "green" if code == 0 else "red"
                self.console.print(f"  [{color}]⚙️ Command finished (exit: {code})[/]")

    def _render_tool_calls(self, tool_calls: list[dict[str, Any]]) -> None:
        for tc in tool_calls:
            name = tc.get("name", "unknown")
            args = tc.get("args", {})

            if name == "task":
                subagent_type = args.get("subagent_type", "")
                desc = args.get("description", "working...")
                if subagent_type in PHASE_LABELS:
                    icon, label, color = PHASE_LABELS[subagent_type]
                    self.console.print(f"\n  [bold {color}]{icon} Phase: {label}[/]")
                    self.console.print(f"  [dim]{desc[:80]}[/]")
                    self.current_phase = label
                    self.update_status(f"{icon} {label}...")
                else:
                    self.console.print(
                        f"  [bold magenta]→ Delegating:[/] {desc[:60]}..."
                    )
                    self.update_status(f"Working: {desc[:40]}...")
            elif name == "write_todos":
                todos = args.get("todos", [])
                if isinstance(todos, list):
                    self._render_todos(todos)
                else:
                    self.console.print("\n  [bold white]📋 Planning[/]")
            elif name in TOOL_ICONS:
                icon = TOOL_ICONS[name]
                if name == "write_file":
                    self.console.print(
                        f"  {icon} Writing: [yellow]{args.get('file_path', 'file')}[/]"
                    )
                    self.update_status("Writing code...")
                elif name == "read_file":
                    self.console.print(
                        f"  {icon} Reading: [dim]{args.get('file_path', 'file')}[/]"
                    )
                elif name == "execute":
                    cmd = args.get("command", "")
                    self.console.print(f"  {icon} [dim]{cmd[:80]}[/]")
                    self.update_status(f"Running: {cmd[:30]}...")
                elif name in ("glob", "ls"):
                    self.console.print(f"  {icon} [dim]{name}[/]")
                    self.update_status(f"{name}...")
                elif name == "grep":
                    pat = args.get("pattern", "")
                    self.console.print(f"  {icon} Grep: [dim]{pat[:40]}[/]")
            else:
                self.console.print(f"  [dim]→ {name}(...)[/]")
