from collections.abc import AsyncIterator
from pathlib import Path

import pytest

from backend.db_session import create_engine, create_session_factory, initialize_database, session_scope
from backend.events import EventType
from configs.settings import Settings
from workflows.repository import WorkflowRepository
from workflows.retry import RetryPolicy
from workflows.service import WorkflowService
from workflows.states import RunStatus, StepStatus


@pytest.fixture
async def workflow_service(tmp_path: Path) -> AsyncIterator[WorkflowService]:
    settings = Settings(sqlite_path=tmp_path / "workflow.sqlite3")
    engine = create_engine(settings)
    await initialize_database(engine)
    session_factory = create_session_factory(engine)

    async with session_scope(session_factory) as session:
        repository = WorkflowRepository(session)
        yield WorkflowService(
            repository=repository,
            retry_policy=RetryPolicy(max_attempts=3, base_delay_seconds=0.25),
        )

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_start_and_complete_run(workflow_service: WorkflowService) -> None:
    run = await workflow_service.create_run("Collect invoice data")
    assert run.status == RunStatus.QUEUED

    running = await workflow_service.start_run(run.id)
    assert running.status == RunStatus.RUNNING
    assert await workflow_service.can_continue(run.id)

    completed = await workflow_service.complete_run(run.id)
    assert completed.status == RunStatus.COMPLETED
    assert not await workflow_service.can_continue(run.id)


@pytest.mark.asyncio
async def test_step_lifecycle_records_attempts(workflow_service: WorkflowService) -> None:
    run = await workflow_service.create_run("Open billing page")
    step = await workflow_service.create_step(run.id, "Navigate to billing")

    started = await workflow_service.start_step(step.id)
    assert started.status == StepStatus.RUNNING
    assert started.attempts == 1

    completed = await workflow_service.complete_step(step.id)
    assert completed.status == StepStatus.COMPLETED


@pytest.mark.asyncio
async def test_retry_policy_marks_retrying_with_delay(workflow_service: WorkflowService) -> None:
    run = await workflow_service.create_run("Retry browser click")
    step = await workflow_service.create_step(run.id, "Click submit")
    started = await workflow_service.start_step(step.id)

    retrying, delay = await workflow_service.fail_or_retry_step(
        started.id,
        retryable=True,
        reason="Selector detached",
    )

    assert retrying.status == StepStatus.RETRYING
    assert retrying.attempts == 1
    assert delay == 0.25


@pytest.mark.asyncio
async def test_non_retryable_step_failure_is_terminal_for_step(
    workflow_service: WorkflowService,
) -> None:
    run = await workflow_service.create_run("Fail browser action")
    step = await workflow_service.create_step(run.id, "Click missing button")
    started = await workflow_service.start_step(step.id)

    failed, delay = await workflow_service.fail_or_retry_step(
        started.id,
        retryable=False,
        reason="Invalid selector",
    )

    assert failed.status == StepStatus.FAILED
    assert delay is None


@pytest.mark.asyncio
async def test_cancelled_run_cannot_continue(workflow_service: WorkflowService) -> None:
    run = await workflow_service.create_run("Cancelable task")

    cancelled = await workflow_service.cancel_run(run.id)

    assert cancelled.status == RunStatus.CANCELLED
    assert not await workflow_service.can_continue(run.id)
    with pytest.raises(RuntimeError):
        await workflow_service.ensure_not_cancelled(run.id)


@pytest.mark.asyncio
async def test_events_and_artifacts_are_persisted(workflow_service: WorkflowService) -> None:
    run = await workflow_service.create_run("Capture screenshot")
    step = await workflow_service.create_step(run.id, "Take screenshot")
    await workflow_service.emit_event(
        run.id,
        EventType.BROWSER_OBSERVATION,
        "Screenshot captured.",
        step_id=step.id,
        payload={"path": "logs/screenshots/example.png"},
    )
    artifact = await workflow_service.add_artifact(
        run.id,
        kind="screenshot",
        path="logs/screenshots/example.png",
        step_id=step.id,
        metadata={"viewport": "1280x900"},
    )

    events = await workflow_service.repository.list_events(run.id)
    artifacts = await workflow_service.repository.list_artifacts(run.id)

    assert any(event.type == EventType.BROWSER_OBSERVATION for event in events)
    assert artifact.kind == "screenshot"
    assert artifacts[0].metadata == {"viewport": "1280x900"}

