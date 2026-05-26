import functools
import http.server
import socketserver
import threading
from pathlib import Path

import pytest

from agents.browser_smoke_planner import BrowserSmokePlanner
from backend.db_session import create_engine, create_session_factory, initialize_database
from backend.events import EventType
from configs.settings import Settings
from workflows.repository import WorkflowRepository
from workflows.runner import AutonomousWorkflowRunner
from workflows.service import WorkflowService
from workflows.states import RunStatus, StepStatus


@pytest.mark.browser_smoke
@pytest.mark.asyncio
async def test_real_browser_workflow_against_local_page(tmp_path: Path) -> None:
    fixtures_dir = Path(__file__).parent / "fixtures"
    server = socketserver.TCPServer(
        ("127.0.0.1", 0),
        functools.partial(http.server.SimpleHTTPRequestHandler, directory=fixtures_dir),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    smoke_url = f"http://127.0.0.1:{server.server_address[1]}/browser_smoke.html"
    settings = Settings(
        sqlite_path=tmp_path / "browser-smoke.sqlite3",
        logs_dir=tmp_path / "logs",
        browser_headless=True,
        browser_action_timeout_seconds=5,
    )
    engine = create_engine(settings)
    await initialize_database(engine)
    session_factory = create_session_factory(engine)

    async with session_factory() as session:
        service = WorkflowService(WorkflowRepository(session))
        run = await service.create_run("Run browser smoke workflow")
        await session.commit()

    runner = AutonomousWorkflowRunner(
        session_factory=session_factory,
        settings=settings,
        planner=BrowserSmokePlanner(smoke_url),
    )
    await runner.run_existing_run(run.id)

    async with session_factory() as session:
        repository = WorkflowRepository(session)
        completed = await repository.get_run(run.id)
        steps = await repository.list_steps(run.id)
        events = await repository.list_events(run.id)

    await engine.dispose()
    server.shutdown()
    server.server_close()

    assert completed is not None
    assert completed.status == RunStatus.COMPLETED
    assert len(steps) == 5
    assert all(step.status == StepStatus.COMPLETED for step in steps)
    event_types = [event.type for event in events]
    assert EventType.BROWSER_ACTION in event_types
    assert EventType.BROWSER_OBSERVATION in event_types
    assert any(
        "Agent received: hello from browser agent" in str(event.payload)
        for event in events
    )
    assert (tmp_path / "logs" / "screenshots" / str(run.id) / "browser-smoke.png").exists()
