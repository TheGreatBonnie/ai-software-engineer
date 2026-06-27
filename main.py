import sys

from src.config import load_settings
from src.coordinator import build_coordinator
from src.sandbox import managed_sandbox


def main() -> None:
    settings = load_settings()

    if len(sys.argv) < 2:
        print("Usage: python main.py '<software request>'")
        print("Example: python main.py 'Build a CLI todo app with SQLite'")
        sys.exit(1)

    user_request = sys.argv[1]

    print(f"[coordinator] Starting AI Software Engineer...")
    print(f"[coordinator] Model: {settings.model}")
    print(f"[coordinator] Max iterations: {settings.max_iterations}")
    print()

    with managed_sandbox(settings) as backend:
        coordinator = build_coordinator(settings, backend=backend)

        result = coordinator.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            f"{user_request}\n\n"
                            f"IMPORTANT: max_iterations={settings.max_iterations}. "
                            f"Stop and report if you exceed this limit."
                        ),
                    }
                ]
            },
        )

        final_message = result["messages"][-1].content
        print(f"\n[coordinator] Final result:\n{final_message}")


if __name__ == "__main__":
    main()
