from typing import Any

from .base import AgentTool, ToolContext, ToolResult


class EchoTaskTool(AgentTool):
    name = "task.echo"
    description = "Returns the requested task as a simple deterministic tool result."

    async def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        return ToolResult(
            ok=True,
            output={
                "run_id": context.run_id,
                "task": kwargs.get("task", ""),
            },
        )

