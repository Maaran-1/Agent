from .contracts import AgentPlan, PlannedStep
from .planner import AgentPlanner


class BrowserSmokePlanner(AgentPlanner):
    """Deterministic browser workflow used for local smoke tests."""

    def __init__(self, url: str, message: str = "hello from browser agent") -> None:
        self.url = url
        self.message = message

    async def plan(self, task: str) -> AgentPlan:
        return AgentPlan(
            objective=task,
            success_criteria=["The smoke page result text confirms the submitted message."],
            risk_notes=["Local smoke test page only."],
            steps=[
                PlannedStep(
                    objective="Open the smoke test page",
                    tool_name="browser.navigate",
                    tool_args={"url": self.url},
                    expected_observation="Smoke page is loaded.",
                    max_attempts=1,
                ),
                PlannedStep(
                    objective="Fill the message field",
                    tool_name="browser.type_text",
                    tool_args={"selector": "#agent-input", "text": self.message},
                    expected_observation="Message field contains the smoke test message.",
                    max_attempts=1,
                ),
                PlannedStep(
                    objective="Submit the smoke form",
                    tool_name="browser.click",
                    tool_args={"selector": "#submit-button"},
                    expected_observation="Result text is updated.",
                    max_attempts=1,
                ),
                PlannedStep(
                    objective="Extract the result text",
                    tool_name="browser.extract_text",
                    tool_args={"selector": "#result"},
                    expected_observation="The result contains the submitted message.",
                    max_attempts=1,
                ),
                PlannedStep(
                    objective="Capture smoke test screenshot",
                    tool_name="browser.screenshot",
                    tool_args={"screenshot_name": "browser-smoke.png"},
                    expected_observation="Screenshot artifact is captured.",
                    max_attempts=1,
                ),
            ],
        )

