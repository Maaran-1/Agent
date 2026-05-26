from typing import Any
from uuid import UUID

from browser.controller import BrowserController
from browser.models import BrowserAction, BrowserActionResult, BrowserActionType
from browser.session import BrowserSession, BrowserSessionManager
from configs.settings import Settings

from .base import AgentTool, ToolContext, ToolResult


class BrowserControllerProvider:
    """Maintains one reusable browser session per workflow run."""

    def __init__(self, settings: Settings) -> None:
        self.session_manager = BrowserSessionManager(settings)
        self._sessions: dict[UUID, BrowserSession] = {}
        self._controllers: dict[UUID, BrowserController] = {}

    async def get_controller(self, context: ToolContext) -> BrowserController:
        run_id = UUID(context.run_id)
        controller = self._controllers.get(run_id)
        if controller is not None:
            return controller

        session = self.session_manager.create_session(run_id)
        await session.start()
        controller = BrowserController(session)
        self._sessions[run_id] = session
        self._controllers[run_id] = controller
        return controller

    async def close_run(self, run_id: UUID) -> None:
        controller = self._controllers.pop(run_id, None)
        session = self._sessions.pop(run_id, None)
        if controller is not None:
            session = controller.session
        if session is not None:
            await session.close()


class BrowserAgentTool(AgentTool):
    action_type: BrowserActionType

    def __init__(self, provider: BrowserControllerProvider) -> None:
        self.provider = provider

    async def close_run(self, run_id: UUID) -> None:
        await self.provider.close_run(run_id)

    async def run(self, context: ToolContext, **kwargs: Any) -> ToolResult:
        action = self._build_action(**kwargs)
        controller = await self.provider.get_controller(context)
        result = await controller.execute(action)
        return self._to_tool_result(result)

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(type=self.action_type, **kwargs)

    def _to_tool_result(self, result: BrowserActionResult) -> ToolResult:
        output: dict[str, Any] = dict(result.output)
        if result.observation is not None:
            output["observation"] = result.observation.model_dump(mode="json")
        return ToolResult(
            ok=result.ok,
            output=output,
            error=result.error,
            retryable=result.retryable,
        )


class BrowserNavigateTool(BrowserAgentTool):
    name = "browser.navigate"
    description = "Navigate the browser to an HTTP or HTTPS URL."
    action_type = BrowserActionType.NAVIGATE

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(
            type=self.action_type,
            url=kwargs.get("url"),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )


class BrowserClickTool(BrowserAgentTool):
    name = "browser.click"
    description = "Click an element using a CSS selector."
    action_type = BrowserActionType.CLICK

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(
            type=self.action_type,
            selector=kwargs.get("selector"),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )


class BrowserTypeTextTool(BrowserAgentTool):
    name = "browser.type_text"
    description = "Fill text into an element using a CSS selector."
    action_type = BrowserActionType.TYPE_TEXT

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(
            type=self.action_type,
            selector=kwargs.get("selector"),
            text=kwargs.get("text"),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )


class BrowserWaitForSelectorTool(BrowserAgentTool):
    name = "browser.wait_for_selector"
    description = "Wait for an element matching a CSS selector."
    action_type = BrowserActionType.WAIT_FOR_SELECTOR

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(
            type=self.action_type,
            selector=kwargs.get("selector"),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )


class BrowserExtractTextTool(BrowserAgentTool):
    name = "browser.extract_text"
    description = "Extract visible text from a CSS selector, defaulting to body."
    action_type = BrowserActionType.EXTRACT_TEXT

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(
            type=self.action_type,
            selector=kwargs.get("selector"),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )


class BrowserScreenshotTool(BrowserAgentTool):
    name = "browser.screenshot"
    description = "Capture a full-page screenshot."
    action_type = BrowserActionType.SCREENSHOT

    def _build_action(self, **kwargs: Any) -> BrowserAction:
        return BrowserAction(
            type=self.action_type,
            screenshot_name=kwargs.get("screenshot_name"),
            timeout_seconds=kwargs.get("timeout_seconds"),
        )


def register_browser_tools(registry, settings: Settings) -> BrowserControllerProvider:
    provider = BrowserControllerProvider(settings)
    registry.register(BrowserNavigateTool(provider))
    registry.register(BrowserClickTool(provider))
    registry.register(BrowserTypeTextTool(provider))
    registry.register(BrowserWaitForSelectorTool(provider))
    registry.register(BrowserExtractTextTool(provider))
    registry.register(BrowserScreenshotTool(provider))
    return provider
