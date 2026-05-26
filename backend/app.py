from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import UUID

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.db_session import create_engine, create_session_factory, initialize_database
from backend.dependencies import get_session, get_settings_from_app
from backend.logging import configure_logging
from backend.schemas import (
    ArtifactResponse,
    CancelRunRequest,
    CreateRunRequest,
    EventResponse,
    HealthResponse,
    RunResponse,
    StepResponse,
)
from configs.settings import Settings, get_settings
from workflows.repository import WorkflowRepository
from workflows.runner import AutonomousWorkflowRunner
from workflows.service import WorkflowService


def create_app(settings: Settings | None = None) -> FastAPI:
    app_settings = settings or get_settings()
    configure_logging(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.settings = app_settings
        app.state.engine = create_engine(app_settings)
        app.state.session_factory = create_session_factory(app.state.engine)
        await initialize_database(app.state.engine)
        try:
            yield
        finally:
            await app.state.engine.dispose()

    app = FastAPI(title=app_settings.app_name, version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
    if frontend_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=frontend_dir, html=True), name="dashboard")

    @app.get("/health", response_model=HealthResponse)
    async def health(settings: Settings = Depends(get_settings_from_app)) -> HealthResponse:
        return HealthResponse(
            status="ok",
            app_name=settings.app_name,
            environment=settings.environment,
        )

    @app.post("/runs", response_model=RunResponse, status_code=201)
    async def create_run(
        request: CreateRunRequest,
        background_tasks: BackgroundTasks,
        app_request: Request,
        session=Depends(get_session),
    ) -> RunResponse:
        service = WorkflowService(WorkflowRepository(session))
        run = await service.create_run(
            task=request.task.strip(),
            model_profile=request.model_profile,
        )
        await session.commit()
        if request.auto_start:
            runner = AutonomousWorkflowRunner(app_request.app.state.session_factory)
            background_tasks.add_task(runner.run_existing_run, run.id)
        return RunResponse.model_validate(run, from_attributes=True)

    @app.get("/runs/{run_id}", response_model=RunResponse)
    async def get_run(run_id: UUID, session=Depends(get_session)) -> RunResponse:
        repository = WorkflowRepository(session)
        run = await repository.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        return RunResponse.model_validate(run, from_attributes=True)

    @app.post("/runs/{run_id}/cancel", response_model=RunResponse)
    async def cancel_run(
        run_id: UUID,
        request: CancelRunRequest | None = None,
        session=Depends(get_session),
    ) -> RunResponse:
        service = WorkflowService(WorkflowRepository(session))
        existing = await service.repository.get_run(run_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        run = await service.cancel_run(
            run_id,
            reason=request.reason if request else "Run cancelled by operator.",
        )
        return RunResponse.model_validate(run, from_attributes=True)

    @app.get("/runs/{run_id}/steps", response_model=list[StepResponse])
    async def list_steps(run_id: UUID, session=Depends(get_session)) -> list[StepResponse]:
        repository = WorkflowRepository(session)
        if await repository.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        steps = await repository.list_steps(run_id)
        return [StepResponse.model_validate(step, from_attributes=True) for step in steps]

    @app.get("/runs/{run_id}/events", response_model=list[EventResponse])
    async def list_events(run_id: UUID, session=Depends(get_session)) -> list[EventResponse]:
        repository = WorkflowRepository(session)
        if await repository.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        events = await repository.list_events(run_id)
        return [EventResponse.model_validate(event, from_attributes=True) for event in events]

    @app.get("/runs/{run_id}/artifacts", response_model=list[ArtifactResponse])
    async def list_artifacts(run_id: UUID, session=Depends(get_session)) -> list[ArtifactResponse]:
        repository = WorkflowRepository(session)
        if await repository.get_run(run_id) is None:
            raise HTTPException(status_code=404, detail="Run not found.")
        artifacts = await repository.list_artifacts(run_id)
        return [
            ArtifactResponse.model_validate(artifact, from_attributes=True)
            for artifact in artifacts
        ]

    @app.websocket("/runs/{run_id}/events/ws")
    async def run_events_ws(websocket: WebSocket, run_id: UUID) -> None:
        await websocket.accept()
        try:
            await websocket.send_json(
                {
                    "type": "connection.ready",
                    "run_id": str(run_id),
                    "message": "WebSocket event streaming is ready.",
                }
            )
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            return

    return app


app = create_app()
