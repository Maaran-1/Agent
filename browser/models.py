from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, HttpUrl


class BrowserActionType(StrEnum):
    NAVIGATE = "navigate"
    CLICK = "click"
    TYPE_TEXT = "type_text"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    EXTRACT_TEXT = "extract_text"
    SCREENSHOT = "screenshot"
    GET_STATE = "get_state"


class BrowserViewport(BaseModel):
    width: int = Field(default=1280, ge=320, le=3840)
    height: int = Field(default=900, ge=240, le=2160)


class BrowserRuntimeConfig(BaseModel):
    headless: bool = False
    viewport: BrowserViewport = Field(default_factory=BrowserViewport)
    action_timeout_seconds: float = Field(default=20.0, gt=0)
    screenshot_dir: Path = Path("logs/screenshots")
    browser_channel: str | None = None
    slow_mo_ms: int = Field(default=0, ge=0)


class BrowserAction(BaseModel):
    type: BrowserActionType
    url: HttpUrl | None = None
    selector: str | None = None
    text: str | None = None
    timeout_seconds: float | None = Field(default=None, gt=0)
    screenshot_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrowserObservation(BaseModel):
    run_id: UUID
    url: str | None = None
    title: str | None = None
    text_preview: str | None = None
    screenshot_path: Path | None = None
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrowserActionResult(BaseModel):
    ok: bool
    action_type: BrowserActionType
    observation: BrowserObservation | None = None
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    retryable: bool = False

