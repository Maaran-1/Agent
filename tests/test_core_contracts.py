from uuid import uuid4

from agents.contracts import AgentPlan, PlannedStep, ReflectionDecision, ReflectionResult
from backend.events import AgentEvent, EventType
from memory.models import LongTermMemory, MemoryType, ShortTermMemory
from workflows.states import RunStatus, is_terminal_run_status


def test_agent_event_has_versioned_wire_type() -> None:
    event = AgentEvent(
        type=EventType.RUN_CREATED,
        run_id=uuid4(),
        message="Run created",
    )

    assert event.version == 1
    assert event.type == "run.created"


def test_terminal_run_statuses_are_explicit() -> None:
    assert is_terminal_run_status(RunStatus.COMPLETED)
    assert is_terminal_run_status(RunStatus.FAILED)
    assert is_terminal_run_status(RunStatus.CANCELLED)
    assert not is_terminal_run_status(RunStatus.RUNNING)


def test_agent_plan_contract_requires_steps() -> None:
    step = PlannedStep(
        objective="Open the target page",
        tool_name="browser.navigate",
        expected_observation="The target page is loaded",
    )
    plan = AgentPlan(
        objective="Research a page",
        success_criteria=["Relevant page content is extracted"],
        steps=[step],
    )

    assert plan.steps[0].max_attempts == 3


def test_reflection_result_records_next_action() -> None:
    result = ReflectionResult(
        decision=ReflectionDecision.REPLAN,
        reason="The page changed unexpectedly",
        memory_notes=["Selector changed after login"],
    )

    assert result.decision == "replan"
    assert result.memory_notes


def test_memory_models_separate_run_context_from_long_term_memory() -> None:
    run_id = uuid4()
    short_term = ShortTermMemory(run_id=run_id, objective="Complete browser task")
    long_term = LongTermMemory(
        type=MemoryType.TASK_PATTERN,
        content="Use search before direct navigation on this site.",
        source="test",
        confidence=0.9,
    )

    assert short_term.run_id == run_id
    assert long_term.confidence == 0.9
