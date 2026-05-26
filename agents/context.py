from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from memory.models import ShortTermMemory
from workflows.states import RunStatus

from .contracts import AgentPlan


class AgentRunContext(BaseModel):
    run_id: UUID = Field(default_factory=uuid4)
    task: str
    status: RunStatus = RunStatus.QUEUED
    plan: AgentPlan | None = None
    memory: ShortTermMemory | None = None
    current_step_index: int = 0

    def initialize_memory(self) -> None:
        self.memory = ShortTermMemory(run_id=self.run_id, objective=self.task)

    def has_more_steps(self) -> bool:
        if self.plan is None:
            return False
        return self.current_step_index < len(self.plan.steps)

