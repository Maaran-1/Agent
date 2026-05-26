from typing import Any

import pytest

from agents.contracts import AgentPlan, PlannedStep
from agents.executor import AgentExecutor
from agents.planner import AgentPlanner, DeterministicPlanner
from backend.events import EventType
from tools.base import AgentTool, ToolContext, ToolRegistry, ToolResult
from tools.echo import EchoTaskTool
from workflows.states import RunStatus


class FlakyTool(AgentTool):
    name = "test.flaky"
    description = "Fails once and then succeeds."

    def __init__(self) -> None:
        self.calls = 0

    async def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        self.calls += 1
        if self.calls == 1:
            return ToolResult(ok=False, error="Temporary failure", retryable=True)
        return ToolResult(ok=True, output={"calls": self.calls})


class FailingTool(AgentTool):
    name = "test.fail"
    description = "Always fails without retry."

    async def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        return ToolResult(ok=False, error="Permanent failure", retryable=False)


class StaticPlanner(AgentPlanner):
    def __init__(self, step: PlannedStep) -> None:
        self.step = step

    async def plan(self, task: str) -> AgentPlan:
        return AgentPlan(
            objective=task,
            success_criteria=["Step succeeds"],
            steps=[self.step],
        )


@pytest.mark.asyncio
async def test_deterministic_agent_loop_completes_and_records_events() -> None:
    registry = ToolRegistry()
    registry.register(EchoTaskTool())
    executor = AgentExecutor(planner=DeterministicPlanner(), tools=registry)

    context = await executor.run("Open a browser task")

    event_types = [event.type for event in executor.events.events]
    assert context.status == RunStatus.COMPLETED
    assert EventType.RUN_CREATED in event_types
    assert EventType.RUN_PLANNING in event_types
    assert EventType.STEP_STARTED in event_types
    assert EventType.BROWSER_ACTION in event_types
    assert EventType.BROWSER_OBSERVATION in event_types
    assert EventType.REFLECTION_DECISION in event_types
    assert EventType.STEP_COMPLETED in event_types
    assert EventType.RUN_COMPLETED in event_types


@pytest.mark.asyncio
async def test_executor_retries_retryable_failure() -> None:
    tool = FlakyTool()
    registry = ToolRegistry()
    registry.register(tool)
    planner = StaticPlanner(
        PlannedStep(
            objective="Run flaky tool",
            tool_name=tool.name,
            expected_observation="Tool eventually succeeds",
            max_attempts=2,
        )
    )
    executor = AgentExecutor(planner=planner, tools=registry)

    context = await executor.run("Retry a temporary failure")

    assert context.status == RunStatus.COMPLETED
    assert tool.calls == 2
    assert context.memory is not None
    assert context.memory.retry_history == ["Temporary failure"]


@pytest.mark.asyncio
async def test_executor_fails_non_retryable_failure() -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())
    planner = StaticPlanner(
        PlannedStep(
            objective="Run failing tool",
            tool_name="test.fail",
            expected_observation="Tool fails",
        )
    )
    executor = AgentExecutor(planner=planner, tools=registry)

    context = await executor.run("Fail safely")

    event_types = [event.type for event in executor.events.events]
    assert context.status == RunStatus.FAILED
    assert EventType.STEP_FAILED in event_types
    assert EventType.RUN_FAILED in event_types


def test_tool_registry_names_are_sorted() -> None:
    registry = ToolRegistry()
    registry.register(FailingTool())
    registry.register(EchoTaskTool())

    assert registry.names() == ["task.echo", "test.fail"]

