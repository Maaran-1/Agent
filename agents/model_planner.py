import json
from typing import Any

from pydantic import ValidationError

from .contracts import AgentPlan
from .ollama import ModelProfile, OllamaClient
from .planner import AgentPlanner
from .prompts import build_planner_prompt


class ModelPlanner(AgentPlanner):
    """Planner backed by Ollama with structured JSON output."""

    def __init__(self, client: OllamaClient, profile: ModelProfile) -> None:
        self.client = client
        self.profile = profile

    async def plan(self, task: str) -> AgentPlan:
        prompt = build_planner_prompt(task)
        raw = await self.client.generate(prompt, self.profile, format_="json")
        payload = self._parse_json(raw)
        return AgentPlan.model_validate(payload)

    def _parse_json(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.strip("`")
            if cleaned.startswith("json"):
                cleaned = cleaned[4:].strip()

        try:
            payload = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ValueError("Model planner returned invalid JSON.") from exc

        if not isinstance(payload, dict):
            raise ValueError("Model planner JSON must be an object.")
        return payload


class FallbackPlanner(AgentPlanner):
    """Uses a primary planner and falls back if model planning fails."""

    def __init__(self, primary: AgentPlanner, fallback: AgentPlanner) -> None:
        self.primary = primary
        self.fallback = fallback
        self.last_error: str | None = None

    async def plan(self, task: str) -> AgentPlan:
        try:
            self.last_error = None
            return await self.primary.plan(task)
        except Exception as exc:
            self.last_error = str(exc)
            return await self.fallback.plan(task)
