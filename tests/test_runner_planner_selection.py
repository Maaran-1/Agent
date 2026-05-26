from configs.settings import Settings
from workflows.runner import create_default_planner


def test_default_planner_is_deterministic_when_ollama_disabled() -> None:
    planner = create_default_planner(Settings(use_ollama_planner=False))

    assert planner.__class__.__name__ == "DeterministicPlanner"


def test_default_planner_uses_fallback_when_ollama_enabled() -> None:
    planner = create_default_planner(
        Settings(use_ollama_planner=True, default_planner_model="gemma4")
    )

    assert planner.__class__.__name__ == "FallbackPlanner"

