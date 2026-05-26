from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from browser.controller import BrowserController
from browser.models import (
    BrowserAction,
    BrowserActionType,
    BrowserRuntimeConfig,
    BrowserViewport,
)
from browser.session import BrowserSession, BrowserSessionManager
from configs.settings import Settings


def test_browser_runtime_config_has_safe_defaults() -> None:
    config = BrowserRuntimeConfig()

    assert config.viewport.width == 1280
    assert config.viewport.height == 900
    assert config.action_timeout_seconds == 20.0
    assert config.screenshot_dir == Path("logs/screenshots")


def test_browser_viewport_rejects_tiny_sizes() -> None:
    with pytest.raises(ValidationError):
        BrowserViewport(width=100, height=100)


def test_browser_action_requires_positive_timeout() -> None:
    with pytest.raises(ValidationError):
        BrowserAction(type=BrowserActionType.GET_STATE, timeout_seconds=0)


def test_session_manager_maps_settings_to_runtime_config(tmp_path: Path) -> None:
    settings = Settings(
        logs_dir=tmp_path / "logs",
        browser_headless=True,
        browser_action_timeout_seconds=12.5,
    )
    manager = BrowserSessionManager(settings)

    config = manager.build_config()

    assert config.headless is True
    assert config.action_timeout_seconds == 12.5
    assert config.screenshot_dir == tmp_path / "logs" / "screenshots"


def test_screenshot_path_is_scoped_and_sanitized(tmp_path: Path) -> None:
    run_id = uuid4()
    session = BrowserSession(
        run_id=run_id,
        config=BrowserRuntimeConfig(screenshot_dir=tmp_path),
    )
    controller = BrowserController(session)

    path = controller._build_screenshot_path("first page?.png")

    assert path == tmp_path / str(run_id) / "first_page_.png"

