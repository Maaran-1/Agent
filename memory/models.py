from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    USER_PREFERENCE = "user_preference"
    TASK_PATTERN = "task_pattern"
    DOMAIN_NOTE = "domain_note"
    TOOL_LESSON = "tool_lesson"
    RUN_SUMMARY = "run_summary"


class ShortTermMemory(BaseModel):
    run_id: UUID
    objective: str
    completed_steps: list[str] = Field(default_factory=list)
    observations: list[str] = Field(default_factory=list)
    retry_history: list[str] = Field(default_factory=list)
    active_hypotheses: list[str] = Field(default_factory=list)


class LongTermMemory(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: MemoryType
    content: str
    source: str
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

