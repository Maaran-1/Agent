import pytest

from agents.contracts import AgentPlan
from agents.model_planner import FallbackPlanner, ModelPlanner
from agents.ollama import ModelProfile
from agents.planner import AgentPlanner, DeterministicPlanner


class FakeOllamaClient:
    def __init__(self, response: str) -> None:
        self.response = response
        self.last_prompt: str | None = None
        self.last_profile: ModelProfile | None = None

    async def generate(self, prompt: str, profile: ModelProfile, format_: str | None = "json") -> str:
        self.last_prompt = prompt
        self.last_profile = profile
        return self.response


class BrokenPlanner(AgentPlanner):
    async def plan(self, task: str) -> AgentPlan:
        raise ValueError("model unavailable")


@pytest.mark.asyncio
async def test_model_planner_parses_structured_plan() -> None:
    client = FakeOllamaClient(
        """
        {
          "objective": "Inspect a page",
          "success_criteria": ["Page inspection result is returned"],
          "risk_notes": ["No browser side effects"],
          "steps": [
            {
              "objective": "Echo task",
              "tool_name": "task.echo",
              "tool_args": {"task": "Inspect a page"},
              "expected_observation": "The task is echoed",
              "max_attempts": 1
            }
          ]
        }
        """
    )
    planner = ModelPlanner(client, ModelProfile(name="planner", model="gemma4"))

    plan = await planner.plan("Inspect a page")

    assert plan.objective == "Inspect a page"
    assert plan.steps[0].tool_name == "task.echo"
    assert client.last_profile is not None
    assert client.last_profile.model == "gemma4"


@pytest.mark.asyncio
async def test_model_planner_rejects_invalid_json() -> None:
    planner = ModelPlanner(
        FakeOllamaClient("not-json"),
        ModelProfile(name="planner", model="gemma4"),
    )

    with pytest.raises(ValueError):
        await planner.plan("Do work")


@pytest.mark.asyncio
async def test_fallback_planner_uses_deterministic_plan_on_model_error() -> None:
    planner = FallbackPlanner(
        primary=BrokenPlanner(),
        fallback=DeterministicPlanner(),
    )

    plan = await planner.plan("Fallback task")

    assert planner.last_error == "model unavailable"
    assert plan.steps[0].tool_name == "task.echo"
    assert plan.steps[0].tool_args == {"task": "Fallback task"}

