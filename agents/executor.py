from backend.events import AgentEvent, EventType
from tools.base import ToolContext, ToolRegistry, ToolResult
from workflows.states import RunStatus

from .context import AgentRunContext
from .contracts import PlannedStep, ReflectionDecision
from .events import EventRecorder
from .planner import AgentPlanner
from .reflection import ReflectionEngine


class AgentExecutor:
    """Coordinates planning, tool execution, reflection, and event emission."""

    def __init__(
        self,
        planner: AgentPlanner,
        tools: ToolRegistry,
        reflection: ReflectionEngine | None = None,
        events: EventRecorder | None = None,
    ) -> None:
        self.planner = planner
        self.tools = tools
        self.reflection = reflection or ReflectionEngine()
        self.events = events or EventRecorder()

    async def run(self, task: str) -> AgentRunContext:
        context = AgentRunContext(task=task)
        context.initialize_memory()
        self._emit(context, EventType.RUN_CREATED, "Run created.")

        try:
            context.status = RunStatus.PLANNING
            self._emit(context, EventType.RUN_PLANNING, "Planning run.")
            context.plan = await self.planner.plan(task)

            context.status = RunStatus.RUNNING
            while context.has_more_steps():
                step = context.plan.steps[context.current_step_index]
                decision = await self._run_step(context, step)

                if decision == ReflectionDecision.CONTINUE:
                    context.current_step_index += 1
                    continue

                if decision == ReflectionDecision.COMPLETE:
                    context.current_step_index += 1
                    context.status = RunStatus.COMPLETED
                    self._emit(context, EventType.RUN_COMPLETED, "Run completed.")
                    return context

                context.status = RunStatus.FAILED
                self._emit(context, EventType.RUN_FAILED, "Run failed.")
                return context

            context.status = RunStatus.COMPLETED
            self._emit(context, EventType.RUN_COMPLETED, "Run completed.")
            return context
        except Exception as exc:
            context.status = RunStatus.FAILED
            self._emit(context, EventType.RUN_FAILED, f"Run failed: {exc}")
            return context

    async def _run_step(
        self,
        context: AgentRunContext,
        step: PlannedStep,
    ) -> ReflectionDecision:
        attempt = 1
        while attempt <= step.max_attempts:
            self._emit(context, EventType.STEP_STARTED, step.objective, step_id=step.id)
            result = await self._call_tool(context, step)
            self._record_result(context, step, result)

            has_more_after_step = (
                context.plan is not None
                and context.current_step_index < len(context.plan.steps) - 1
            )
            reflection = self.reflection.decide(
                result=result,
                attempt=attempt,
                max_attempts=step.max_attempts,
                has_more_steps=has_more_after_step,
            )
            self._emit(
                context,
                EventType.REFLECTION_DECISION,
                reflection.reason,
                step_id=step.id,
                payload={"decision": reflection.decision.value},
            )

            if reflection.decision == ReflectionDecision.RETRY:
                attempt += 1
                continue

            if reflection.decision in {ReflectionDecision.CONTINUE, ReflectionDecision.COMPLETE}:
                self._emit(context, EventType.STEP_COMPLETED, step.objective, step_id=step.id)
            else:
                self._emit(context, EventType.STEP_FAILED, step.objective, step_id=step.id)

            return reflection.decision

        self._emit(context, EventType.STEP_FAILED, step.objective, step_id=step.id)
        return ReflectionDecision.FAIL

    async def _call_tool(self, context: AgentRunContext, step: PlannedStep) -> ToolResult:
        tool = self.tools.get(step.tool_name)
        tool_context = ToolContext(run_id=str(context.run_id), step_id=str(step.id))
        self._emit(
            context,
            EventType.BROWSER_ACTION,
            f"Calling tool {step.tool_name}.",
            step_id=step.id,
            payload={"tool_name": step.tool_name, "tool_args": step.tool_args},
        )
        return await tool.run(tool_context, **step.tool_args)

    def _record_result(
        self,
        context: AgentRunContext,
        step: PlannedStep,
        result: ToolResult,
    ) -> None:
        if context.memory is not None:
            if result.ok:
                context.memory.completed_steps.append(step.objective)
                context.memory.observations.append(str(result.output))
            else:
                context.memory.retry_history.append(result.error or "Unknown tool failure")

        self._emit(
            context,
            EventType.BROWSER_OBSERVATION,
            "Tool result recorded.",
            step_id=step.id,
            payload={
                "ok": result.ok,
                "output": result.output,
                "error": result.error,
                "retryable": result.retryable,
            },
        )

    def _emit(
        self,
        context: AgentRunContext,
        event_type: EventType,
        message: str,
        step_id=None,
        payload: dict | None = None,
    ) -> None:
        self.events.emit(
            AgentEvent(
                type=event_type,
                run_id=context.run_id,
                step_id=step_id,
                message=message,
                payload=payload or {},
            )
        )

