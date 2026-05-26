from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class EventType(StrEnum):
    RUN_CREATED = "run.created"
    RUN_PLANNING = "run.planning"
    STEP_STARTED = "step.started"
    BROWSER_ACTION = "browser.action"
    BROWSER_OBSERVATION = "browser.observation"
    REFLECTION_DECISION = "reflection.decision"
    MEMORY_WRITE = "memory.write"
    STEP_COMPLETED = "step.completed"
    STEP_FAILED = "step.failed"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"


class AgentEvent(BaseModel):
    """Versioned event sent to logs, storage, and WebSocket clients."""

    model_config = ConfigDict(use_enum_values=True)

    id: UUID = Field(default_factory=uuid4)
    version: int = 1
    type: EventType
    run_id: UUID
    step_id: UUID | None = None
    message: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

