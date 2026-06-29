import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.traceback import install

from src.config import load_settings
from src.display import AgentDisplay
from src.sandbox import managed_sandbox
from src.pipeline import WorkflowPipeline


def download_artifacts(backend, files: list[str], console: Console) -> None:
    if not files:
        sandbox_result = backend.execute(
            "find / -maxdepth 5 -type f ! -path '*/.*' "
            "! -path '/proc/*' ! -path '/sys/*' ! -path '/dev/*' "
            "! -path '/usr/*' ! -path '/lib/*' ! -path '/etc/*' "
            "! -path '/var/*' 2>/dev/null"
        )
        files = [f.strip() for f in sandbox_result.output.splitlines() if f.strip()]

    if not files:
        console.print("  [yellow]No files found in sandbox[/]")
        return

    downloads = backend.download_files(files)
    for dl in downloads:
        if dl.content is not None:
            target = Path("output") / dl.path.lstrip("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(dl.content)
            console.print(f"  [green]✓[/] {dl.path}")
        else:
            console.print(f"  [red]✗[/] {dl.path} — {dl.error}")


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
        f"Quality gates: [green]enabled[/green]\n"
        f"Request: [white]{user_request[:80]}{'...' if len(user_request) > 80 else ''}[/white]",
        border_style="blue",
    ))

    with managed_sandbox(settings) as backend:
        pipeline = WorkflowPipeline(settings, backend=backend)
        display = AgentDisplay(console)

        pipeline.on("phase_start", display.on_phase_start)
        pipeline.on("gate_result", display.on_gate_result)
        pipeline.on("phase_output", display.on_phase_output)
        pipeline.on("pipeline_complete", display.on_pipeline_complete)

        result = pipeline.run(user_request)

        console.print("\n[bold blue]━━━ Downloading artifacts ━━━[/]")
        download_artifacts(backend, result.files, console)

    console.print()
    status_icon = "✓" if result.status == "completed" else "⚠" if result.status == "escalated" else "✗"
    console.print(f"[bold green]━━━ {status_icon} {result.status.upper()} ({result.elapsed_seconds:.1f}s) ━━━[/]")
    if result.error:
        console.print(f"[bold red]Error:[/] {result.error}")


if __name__ == "__main__":
    main()
