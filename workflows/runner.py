from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from agents.contracts import ReflectionDecision
from agents.model_planner import FallbackPlanner, ModelPlanner
from agents.ollama import OllamaClient, planner_profile
from agents.planner import AgentPlanner, DeterministicPlanner
from agents.reflection import ReflectionEngine
from backend.events import EventType
from configs.settings import Settings
from tools.base import ToolContext, ToolRegistry, ToolResult
from tools.echo import EchoTaskTool

from .models import WorkflowRun
from .repository import WorkflowRepository
from .service import WorkflowService
from .states import RunStatus


def create_default_tool_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(EchoTaskTool())
    return registry


def create_default_planner(settings: Settings) -> AgentPlanner:
    deterministic = DeterministicPlanner()
    if not settings.use_ollama_planner:
        return deterministic

    model_planner = ModelPlanner(
        client=OllamaClient(settings.ollama_base_url),
        profile=planner_profile(settings.default_planner_model),
    )
    return FallbackPlanner(primary=model_planner, fallback=deterministic)


class AutonomousWorkflowRunner:
    """Executes stored workflow runs using planner, tools, and reflection."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        settings: Settings | None = None,
        planner: AgentPlanner | None = None,
        tools: ToolRegistry | None = None,
        reflection: ReflectionEngine | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.settings = settings
        self.planner = planner or (
            create_default_planner(settings) if settings is not None else DeterministicPlanner()
        )
        self.tools = tools or create_default_tool_registry()
        self.reflection = reflection or ReflectionEngine()

    async def run_existing_run(self, run_id) -> None:
        async with self.session_factory() as session:
            repository = WorkflowRepository(session)
            service = WorkflowService(repository)
            run = await repository.get_run(run_id)
            if run is None:
                return

            try:
                await service.start_run(run.id)
                await session.commit()
                await self._execute_run(run, service)
                await session.commit()
            except RuntimeError as exc:
                current = await repository.get_run(run.id)
                if current is not None and current.status == RunStatus.CANCELLED:
                    await session.commit()
                    return
                await service.fail_run(run.id, str(exc))
                await session.commit()
            except Exception as exc:  # pragma: no cover - defensive runtime boundary
                await service.fail_run(run.id, f"Autonomous workflow failed: {exc}")
                await session.commit()

    async def _execute_run(self, run: WorkflowRun, service: WorkflowService) -> None:
        plan = await self.planner.plan(run.task)
        await service.emit_event(
            run.id,
            EventType.RUN_PLANNING,
            "Plan created.",
            payload={
                "objective": plan.objective,
                "step_count": len(plan.steps),
                "success_criteria": plan.success_criteria,
                "planner": self.planner.__class__.__name__,
            },
        )

        for planned_step in plan.steps:
            await service.ensure_not_cancelled(run.id)
            step = await service.create_step(run.id, planned_step.objective)

            attempt = 1
            while attempt <= planned_step.max_attempts:
                await service.ensure_not_cancelled(run.id)
                started_step = await service.start_step(step.id)
                tool_result = await self._call_tool(run, started_step.id, planned_step, service)

                has_more_steps = planned_step.id != plan.steps[-1].id
                reflection = self.reflection.decide(
                    result=tool_result,
                    attempt=attempt,
                    max_attempts=planned_step.max_attempts,
                    has_more_steps=has_more_steps,
                )
                await service.emit_event(
                    run.id,
                    EventType.REFLECTION_DECISION,
                    reflection.reason,
                    step_id=started_step.id,
                    payload={"decision": reflection.decision.value},
                )

                if reflection.decision == ReflectionDecision.RETRY:
                    await service.fail_or_retry_step(
                        started_step.id,
                        retryable=True,
                        reason=reflection.reason,
                    )
                    attempt += 1
                    continue

                if reflection.decision in {
                    ReflectionDecision.CONTINUE,
                    ReflectionDecision.COMPLETE,
                }:
                    await service.complete_step(started_step.id)
                    break

                await service.fail_or_retry_step(
                    started_step.id,
                    retryable=False,
                    reason=reflection.reason,
                )
                await service.fail_run(run.id, reflection.reason)
                return

        await service.complete_run(run.id)

    async def _call_tool(self, run, step_id, planned_step, service: WorkflowService) -> ToolResult:
        tool = self.tools.get(planned_step.tool_name)
        await service.emit_event(
            run.id,
            EventType.BROWSER_ACTION,
            f"Calling tool {planned_step.tool_name}.",
            step_id=step_id,
            payload={
                "tool_name": planned_step.tool_name,
                "tool_args": planned_step.tool_args,
            },
        )
        result = await tool.run(
            ToolContext(run_id=str(run.id), step_id=str(step_id)),
            **planned_step.tool_args,
        )
        await service.emit_event(
            run.id,
            EventType.BROWSER_OBSERVATION,
            "Tool result recorded.",
            step_id=step_id,
            payload={
                "ok": result.ok,
                "output": result.output,
                "error": result.error,
                "retryable": result.retryable,
            },
        )
        return result
