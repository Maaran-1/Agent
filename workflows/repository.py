from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import ArtifactRecord, EventRecord, RunRecord, StepRecord
from backend.events import AgentEvent

from .models import WorkflowArtifact, WorkflowRun, WorkflowStep
from .states import RunStatus, StepStatus


class WorkflowRepository:
    """Persistence layer for workflow runs, steps, events, and artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(self, task: str, model_profile: str = "gemma4") -> WorkflowRun:
        record = RunRecord(task=task, model_profile=model_profile)
        self.session.add(record)
        await self.session.flush()
        return self._run_to_model(record)

    async def get_run(self, run_id: UUID) -> WorkflowRun | None:
        record = await self.session.get(RunRecord, str(run_id))
        return self._run_to_model(record) if record else None

    async def update_run_status(self, run_id: UUID, status: RunStatus) -> WorkflowRun:
        record = await self.session.get(RunRecord, str(run_id))
        if record is None:
            raise ValueError(f"Run not found: {run_id}")
        record.status = status.value
        await self.session.flush()
        return self._run_to_model(record)

    async def create_step(self, run_id: UUID, objective: str) -> WorkflowStep:
        record = StepRecord(run_id=str(run_id), objective=objective)
        self.session.add(record)
        await self.session.flush()
        return self._step_to_model(record)

    async def list_steps(self, run_id: UUID) -> list[WorkflowStep]:
        statement = select(StepRecord).where(StepRecord.run_id == str(run_id))
        records = (await self.session.scalars(statement)).all()
        return [self._step_to_model(record) for record in records]

    async def update_step_status(
        self,
        step_id: UUID,
        status: StepStatus,
        attempts: int | None = None,
    ) -> WorkflowStep:
        record = await self.session.get(StepRecord, str(step_id))
        if record is None:
            raise ValueError(f"Step not found: {step_id}")
        record.status = status.value
        if attempts is not None:
            record.attempts = attempts
        await self.session.flush()
        return self._step_to_model(record)

    async def increment_step_attempts(self, step_id: UUID) -> WorkflowStep:
        record = await self.session.get(StepRecord, str(step_id))
        if record is None:
            raise ValueError(f"Step not found: {step_id}")
        record.attempts += 1
        await self.session.flush()
        return self._step_to_model(record)

    async def persist_event(self, event: AgentEvent) -> AgentEvent:
        record = EventRecord(
            id=str(event.id),
            run_id=str(event.run_id),
            step_id=str(event.step_id) if event.step_id else None,
            type=event.type,
            message=event.message,
            payload=event.payload,
            created_at=event.created_at,
        )
        self.session.add(record)
        await self.session.flush()
        return event

    async def list_events(self, run_id: UUID) -> list[AgentEvent]:
        statement = (
            select(EventRecord)
            .where(EventRecord.run_id == str(run_id))
            .order_by(EventRecord.created_at.asc())
        )
        records = (await self.session.scalars(statement)).all()
        return [self._event_to_model(record) for record in records]

    async def create_artifact(
        self,
        run_id: UUID,
        kind: str,
        path: str,
        step_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> WorkflowArtifact:
        record = ArtifactRecord(
            run_id=str(run_id),
            step_id=str(step_id) if step_id else None,
            kind=kind,
            path=path,
            metadata_=metadata or {},
        )
        self.session.add(record)
        await self.session.flush()
        return self._artifact_to_model(record)

    async def list_artifacts(self, run_id: UUID) -> list[WorkflowArtifact]:
        statement = select(ArtifactRecord).where(ArtifactRecord.run_id == str(run_id))
        records = (await self.session.scalars(statement)).all()
        return [self._artifact_to_model(record) for record in records]

    def _run_to_model(self, record: RunRecord) -> WorkflowRun:
        return WorkflowRun(
            id=UUID(record.id),
            task=record.task,
            status=RunStatus(record.status),
            model_profile=record.model_profile,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _step_to_model(self, record: StepRecord) -> WorkflowStep:
        return WorkflowStep(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            objective=record.objective,
            status=StepStatus(record.status),
            attempts=record.attempts,
            created_at=record.created_at,
            updated_at=record.updated_at,
        )

    def _event_to_model(self, record: EventRecord) -> AgentEvent:
        return AgentEvent(
            id=UUID(record.id),
            type=record.type,
            run_id=UUID(record.run_id),
            step_id=UUID(record.step_id) if record.step_id else None,
            message=record.message,
            payload=record.payload or {},
            created_at=record.created_at,
        )

    def _artifact_to_model(self, record: ArtifactRecord) -> WorkflowArtifact:
        return WorkflowArtifact(
            id=UUID(record.id),
            run_id=UUID(record.run_id),
            step_id=UUID(record.step_id) if record.step_id else None,
            kind=record.kind,
            path=record.path,
            metadata=record.metadata_ or {},
            created_at=record.created_at,
        )

