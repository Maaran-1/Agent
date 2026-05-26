from configs.settings import Settings
from workflows.runner import create_default_planner, create_default_tool_registry


def test_default_planner_is_deterministic_when_ollama_disabled() -> None:
    planner = create_default_planner(Settings(use_ollama_planner=False))

    assert planner.__class__.__name__ == "DeterministicPlanner"


def test_default_planner_uses_fallback_when_ollama_enabled() -> None:
    planner = create_default_planner(
        Settings(use_ollama_planner=True, default_planner_model="gemma4")
    )

    assert planner.__class__.__name__ == "FallbackPlanner"


def test_default_tool_registry_includes_browser_tools_when_settings_are_available() -> None:
    registry = create_default_tool_registry(Settings())

    assert "task.echo" in registry.names()
    assert "browser.navigate" in registry.names()
