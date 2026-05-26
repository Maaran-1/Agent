from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from workflows.states import RunStatus, StepStatus


class CreateRunRequest(BaseModel):
    task: str = Field(min_length=1)
    model_profile: str = "gemma4"
    auto_start: bool = True


class RunResponse(BaseModel):
    id: UUID
    task: str
    status: RunStatus
    model_profile: str
    created_at: datetime
    updated_at: datetime


class StepResponse(BaseModel):
    id: UUID
    run_id: UUID
    objective: str
    status: StepStatus
    attempts: int
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    id: UUID
    version: int
    type: str
    run_id: UUID
    step_id: UUID | None = None
    message: str
    payload: dict
    created_at: datetime


class ArtifactResponse(BaseModel):
    id: UUID
    run_id: UUID
    step_id: UUID | None = None
    kind: str
    path: Path
    metadata: dict
    created_at: datetime


class CancelRunRequest(BaseModel):
    reason: str = "Run cancelled by operator."


class HealthResponse(BaseModel):
    status: str
    app_name: str
    environment: str
