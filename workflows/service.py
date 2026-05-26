from uuid import UUID

from backend.events import AgentEvent, EventType

from .models import WorkflowArtifact, WorkflowRun, WorkflowStep
from .repository import WorkflowRepository
from .retry import RetryPolicy
from .states import RunStatus, StepStatus, is_terminal_run_status


class WorkflowService:
    """Coordinates durable workflow state transitions."""

    def __init__(
        self,
        repository: WorkflowRepository,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.repository = repository
        self.retry_policy = retry_policy or RetryPolicy()

    async def create_run(self, task: str, model_profile: str = "gemma4") -> WorkflowRun:
        run = await self.repository.create_run(task=task, model_profile=model_profile)
        await self.emit_event(run.id, EventType.RUN_CREATED, "Run created.")
        return run

    async def create_step(self, run_id: UUID, objective: str) -> WorkflowStep:
        return await self.repository.create_step(run_id=run_id, objective=objective)

    async def start_run(self, run_id: UUID) -> WorkflowRun:
        run = await self.repository.update_run_status(run_id, RunStatus.RUNNING)
        await self.emit_event(run.id, EventType.RUN_PLANNING, "Run started.")
        return run

    async def complete_run(self, run_id: UUID) -> WorkflowRun:
        run = await self.repository.update_run_status(run_id, RunStatus.COMPLETED)
        await self.emit_event(run.id, EventType.RUN_COMPLETED, "Run completed.")
        return run

    async def fail_run(self, run_id: UUID, reason: str) -> WorkflowRun:
        run = await self.repository.update_run_status(run_id, RunStatus.FAILED)
        await self.emit_event(run.id, EventType.RUN_FAILED, reason)
        return run

    async def cancel_run(self, run_id: UUID, reason: str = "Run cancelled.") -> WorkflowRun:
        run = await self.repository.update_run_status(run_id, RunStatus.CANCELLED)
        await self.emit_event(run.id, EventType.RUN_CANCELLED, reason)
        return run

    async def ensure_not_cancelled(self, run_id: UUID) -> None:
        run = await self.repository.get_run(run_id)
        if run is None:
            raise ValueError(f"Run not found: {run_id}")
        if run.status == RunStatus.CANCELLED:
            raise RuntimeError(f"Run is cancelled: {run_id}")

    async def start_step(self, step_id: UUID) -> WorkflowStep:
        step = await self.repository.increment_step_attempts(step_id)
        step = await self.repository.update_step_status(
            step.id,
            StepStatus.RUNNING,
            attempts=step.attempts,
        )
        await self.emit_event(step.run_id, EventType.STEP_STARTED, step.objective, step.id)
        return step

    async def complete_step(self, step_id: UUID) -> WorkflowStep:
        step = await self.repository.update_step_status(step_id, StepStatus.COMPLETED)
        await self.emit_event(step.run_id, EventType.STEP_COMPLETED, step.objective, step.id)
        return step

    async def fail_or_retry_step(
        self,
        step_id: UUID,
        retryable: bool,
        reason: str,
    ) -> tuple[WorkflowStep, float | None]:
        step = await self.repository.update_step_status(step_id, StepStatus.FAILED)
        if self.retry_policy.should_retry(step.attempts, retryable):
            step = await self.repository.update_step_status(
                step.id,
                StepStatus.RETRYING,
                attempts=step.attempts,
            )
            delay = self.retry_policy.delay_for_attempt(step.attempts)
            await self.emit_event(
                step.run_id,
                EventType.REFLECTION_DECISION,
                reason,
                step.id,
                {"decision": "retry", "delay_seconds": delay},
            )
            return step, delay

        step = await self.repository.update_step_status(
            step.id,
            StepStatus.FAILED,
            attempts=step.attempts,
        )
        await self.emit_event(step.run_id, EventType.STEP_FAILED, reason, step.id)
        return step, None

    async def add_artifact(
        self,
        run_id: UUID,
        kind: str,
        path: str,
        step_id: UUID | None = None,
        metadata: dict | None = None,
    ) -> WorkflowArtifact:
        return await self.repository.create_artifact(
            run_id=run_id,
            step_id=step_id,
            kind=kind,
            path=path,
            metadata=metadata,
        )

    async def emit_event(
        self,
        run_id: UUID,
        event_type: EventType,
        message: str,
        step_id: UUID | None = None,
        payload: dict | None = None,
    ) -> AgentEvent:
        event = AgentEvent(
            type=event_type,
            run_id=run_id,
            step_id=step_id,
            message=message,
            payload=payload or {},
        )
        return await self.repository.persist_event(event)

    async def can_continue(self, run_id: UUID) -> bool:
        run = await self.repository.get_run(run_id)
        return run is not None and not is_terminal_run_status(run.status)
