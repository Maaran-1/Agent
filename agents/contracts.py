from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ReflectionDecision(StrEnum):
    CONTINUE = "continue"
    RETRY = "retry"
    REPLAN = "replan"
    WAIT_FOR_OPERATOR = "wait_for_operator"
    COMPLETE = "complete"
    FAIL = "fail"


class PlannedStep(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    objective: str
    tool_name: str
    tool_args: dict[str, Any] = Field(default_factory=dict)
    expected_observation: str
    max_attempts: int = 3


class AgentPlan(BaseModel):
    objective: str
    success_criteria: list[str]
    risk_notes: list[str] = Field(default_factory=list)
    steps: list[PlannedStep]


class ReflectionResult(BaseModel):
    decision: ReflectionDecision
    reason: str
    next_step_id: UUID | None = None
    memory_notes: list[str] = Field(default_factory=list)

