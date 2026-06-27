def test_imports():
    from src.config import load_settings
    from src.models import Plan
    from src.prompts import COORDINATOR_PROMPT
    from src.coordinator import build_coordinator

    settings = load_settings()
    assert settings.model is not None
    assert len(COORDINATOR_PROMPT) > 100
    assert "planner" in COORDINATOR_PROMPT

    plan = Plan(objective="test", tasks=["a"], dependencies={}, milestones=["m1"])
    assert plan.objective == "test"
