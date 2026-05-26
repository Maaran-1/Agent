from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field


class ToolContext(BaseModel):
    run_id: str
    step_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    ok: bool
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
    retryable: bool = False


class AgentTool(ABC):
    name: str
    description: str

    @abstractmethod
    async def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        """Execute the tool and return a structured result."""

