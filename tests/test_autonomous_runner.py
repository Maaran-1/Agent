from pathlib import Path

import pytest

from backend.db_session import create_engine, create_session_factory, initialize_database
from backend.events import EventType
from configs.settings import Settings
from workflows.repository import WorkflowRepository
from workflows.runner import AutonomousWorkflowRunner
from workflows.service import WorkflowService
from workflows.states import RunStatus, StepStatus


@pytest.mark.asyncio
async def test_runner_executes_existing_run(tmp_path: Path) -> None:
    settings = Settings(sqlite_path=tmp_path / "runner.sqlite3")
    engine = create_engine(settings)
    await initialize_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        service = WorkflowService(WorkflowRepository(session))
        run = await service.create_run("Echo autonomous task")
        await session.commit()

    runner = AutonomousWorkflowRunner(session_factory)
    await runner.run_existing_run(run.id)

    async with session_factory() as session:
        repository = WorkflowRepository(session)
        completed = await repository.get_run(run.id)
        steps = await repository.list_steps(run.id)
        events = await repository.list_events(run.id)

    await engine.dispose()

    assert completed is not None
    assert completed.status == RunStatus.COMPLETED
    assert len(steps) == 1
    assert steps[0].status == StepStatus.COMPLETED
    event_types = [event.type for event in events]
    assert EventType.BROWSER_ACTION in event_types
    assert EventType.BROWSER_OBSERVATION in event_types
    assert EventType.RUN_COMPLETED in event_types

