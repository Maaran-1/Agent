from abc import ABC, abstractmethod

from .contracts import AgentPlan, PlannedStep


class AgentPlanner(ABC):
    @abstractmethod
    async def plan(self, task: str) -> AgentPlan:
        """Create an executable plan for a user task."""


class DeterministicPlanner(AgentPlanner):
    """Small initial planner used before model-backed planning is introduced."""

    async def plan(self, task: str) -> AgentPlan:
        normalized_task = task.strip()
        if not normalized_task:
            raise ValueError("Task cannot be empty.")

        return AgentPlan(
            objective=normalized_task,
            success_criteria=["The task has been executed and a final observation is available."],
            risk_notes=["Initial deterministic planner uses one generic execution step."],
            steps=[
                PlannedStep(
                    objective=normalized_task,
                    tool_name="task.echo",
                    tool_args={"task": normalized_task},
                    expected_observation="The task execution result is returned.",
                )
            ],
        )

