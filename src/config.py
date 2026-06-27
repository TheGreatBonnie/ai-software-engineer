import os
from dataclasses import dataclass, field


@dataclass
class Settings:
    model: str = field(default_factory=lambda: os.getenv(
        "AGENT_MODEL", "openrouter/owl-alpha"
    ))
    e2b_api_key: str = field(default_factory=lambda: os.getenv("E2B_API_KEY", ""))
    max_iterations: int = 10
    sandbox_timeout: int = 300


def load_settings() -> Settings:
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass
    return Settings()
