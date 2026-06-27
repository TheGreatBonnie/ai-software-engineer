import sys

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.traceback import install

from src.config import load_settings
from src.coordinator import build_coordinator
from src.display import AgentDisplay
from src.sandbox import managed_sandbox


def main() -> None:
    install()

    if len(sys.argv) < 2:
        print("Usage: python main.py '<software request>'")
        print("Example: python main.py 'Build a CLI todo app with SQLite'")
        sys.exit(1)

    console = Console()

    settings = load_settings()

    user_request = sys.argv[1]

    console.print(Panel.fit(
        f"[bold]AI Software Engineer[/bold]\n"
        f"Model: [cyan]{settings.model}[/cyan]\n"
        f"Max iterations: [yellow]{settings.max_iterations}[/yellow]\n"
        f"Request: [white]{user_request[:80]}{'...' if len(user_request) > 80 else ''}[/white]",
        border_style="blue",
    ))

    with managed_sandbox(settings) as backend:
        coordinator = build_coordinator(settings, backend=backend)

        display = AgentDisplay(console)

        with Live(
            display.spinner,
            console=console,
            refresh_per_second=10,
            transient=True,
        ) as live:
            for chunk in coordinator.stream(
                {"messages": [{"role": "user", "content": user_request}]},
                stream_mode="updates",
                version="v2",
            ):
                if chunk["type"] != "updates":
                    continue

                data = chunk["data"]
                if data is None:
                    continue
                for _node_name, node_data in data.items():
                    if node_data is None:
                        continue
                    messages = node_data.get("messages")
                    if not messages:
                        continue

                    live.stop()
                    for msg in messages:
                        display.print_message(msg)
                    live.start()
                    live.update(display.spinner)

    console.print()
    console.print("[bold green]━━━ ✓ Complete ━━━[/]")


if __name__ == "__main__":
    main()
