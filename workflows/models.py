from datetime import datetime
from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from .states import RunStatus, StepStatus


class WorkflowRun(BaseModel):
    id: UUID
    task: str
    status: RunStatus
    model_profile: str
    created_at: datetime
    updated_at: datetime


class WorkflowStep(BaseModel):
    id: UUID
    run_id: UUID
    objective: str
    status: StepStatus
    attempts: int
    created_at: datetime
    updated_at: datetime


class WorkflowArtifact(BaseModel):
    id: UUID
    run_id: UUID
    step_id: UUID | None = None
    kind: str
    path: Path
    metadata: dict = Field(default_factory=dict)
    created_at: datetime

