from uuid import uuid4

import pytest

from browser.models import (
    BrowserActionResult,
    BrowserActionType,
    BrowserObservation,
)
from tools.base import ToolContext, ToolRegistry
from tools.browser import (
    BrowserClickTool,
    BrowserControllerProvider,
    BrowserExtractTextTool,
    BrowserNavigateTool,
    BrowserScreenshotTool,
    BrowserTypeTextTool,
    BrowserWaitForSelectorTool,
    register_browser_tools,
)
from configs.settings import Settings


class FakeController:
    def __init__(self, run_id):
        self.run_id = run_id
        self.actions = []

    async def execute(self, action):
        self.actions.append(action)
        return BrowserActionResult(
            ok=True,
            action_type=action.type,
            output={"action": action.type.value},
            observation=BrowserObservation(
                run_id=self.run_id,
                url="https://example.com",
                title="Example",
                text_preview="Example page",
            ),
        )


class FakeProvider:
    def __init__(self):
        self.run_id = uuid4()
        self.controller = FakeController(self.run_id)
        self.closed = []

    async def get_controller(self, context):
        return self.controller

    async def close_run(self, run_id):
        self.closed.append(run_id)


@pytest.mark.asyncio
async def test_browser_navigate_tool_maps_to_browser_action() -> None:
    provider = FakeProvider()
    tool = BrowserNavigateTool(provider)

    result = await tool.run(
        ToolContext(run_id=str(provider.run_id)),
        url="https://example.com",
    )

    assert result.ok
    assert provider.controller.actions[0].type == BrowserActionType.NAVIGATE
    assert str(provider.controller.actions[0].url) == "https://example.com/"
    assert result.output["observation"]["title"] == "Example"


@pytest.mark.asyncio
async def test_browser_tools_build_expected_action_types() -> None:
    provider = FakeProvider()
    context = ToolContext(run_id=str(provider.run_id))

    await BrowserClickTool(provider).run(context, selector="#submit")
    await BrowserTypeTextTool(provider).run(context, selector="#q", text="browser agent")
    await BrowserWaitForSelectorTool(provider).run(context, selector="main")
    await BrowserExtractTextTool(provider).run(context, selector="body")
    await BrowserScreenshotTool(provider).run(context, screenshot_name="page.png")

    assert [action.type for action in provider.controller.actions] == [
        BrowserActionType.CLICK,
        BrowserActionType.TYPE_TEXT,
        BrowserActionType.WAIT_FOR_SELECTOR,
        BrowserActionType.EXTRACT_TEXT,
        BrowserActionType.SCREENSHOT,
    ]


@pytest.mark.asyncio
async def test_registry_closes_shared_browser_provider_once() -> None:
    provider = FakeProvider()
    registry = ToolRegistry()
    registry.register(BrowserNavigateTool(provider))
    registry.register(BrowserClickTool(provider))

    await registry.close_run(provider.run_id)

    assert provider.closed == [provider.run_id]


def test_register_browser_tools_adds_expected_tools() -> None:
    registry = ToolRegistry()

    provider = register_browser_tools(registry, Settings())

    assert isinstance(provider, BrowserControllerProvider)
    assert "browser.navigate" in registry.names()
    assert "browser.screenshot" in registry.names()
