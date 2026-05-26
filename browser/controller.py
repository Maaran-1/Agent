from pathlib import Path
from uuid import UUID

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from .exceptions import BrowserSessionClosedError
from .models import (
    BrowserAction,
    BrowserActionResult,
    BrowserActionType,
    BrowserObservation,
)
from .session import BrowserSession


class BrowserController:
    """Executes typed browser actions against a browser session."""

    def __init__(self, session: BrowserSession) -> None:
        self.session = session

    async def execute(self, action: BrowserAction) -> BrowserActionResult:
        try:
            output = await self._execute_action(action)
            observation = await self.observe(
                screenshot_name=action.screenshot_name
                if action.type == BrowserActionType.SCREENSHOT
                else None
            )
            return BrowserActionResult(
                ok=True,
                action_type=action.type,
                observation=observation,
                output=output,
            )
        except BrowserSessionClosedError as exc:
            return self._failure(action, str(exc), retryable=True)
        except PlaywrightTimeoutError as exc:
            return self._failure(action, f"Browser action timed out: {exc}", retryable=True)
        except PlaywrightError as exc:
            return self._failure(action, f"Browser action failed: {exc}", retryable=True)
        except ValueError as exc:
            return self._failure(action, str(exc), retryable=False)

    async def observe(self, screenshot_name: str | None = None) -> BrowserObservation:
        page = self.session.page
        screenshot_path = None
        errors: list[str] = []

        if screenshot_name:
            screenshot_path = self._build_screenshot_path(screenshot_name)
            await page.screenshot(path=str(screenshot_path), full_page=True)

        try:
            text_preview = await page.locator("body").inner_text(timeout=1000)
            text_preview = text_preview[:2000]
        except PlaywrightError as exc:
            text_preview = None
            errors.append(f"Could not read page text: {exc}")

        return BrowserObservation(
            run_id=self.session.run_id,
            url=page.url,
            title=await page.title(),
            text_preview=text_preview,
            screenshot_path=screenshot_path,
            errors=errors,
        )

    async def _execute_action(self, action: BrowserAction) -> dict:
        page = self.session.page
        timeout_ms = self._timeout_ms(action)

        if action.type == BrowserActionType.NAVIGATE:
            if action.url is None:
                raise ValueError("Navigate action requires url.")
            response = await page.goto(str(action.url), wait_until="domcontentloaded", timeout=timeout_ms)
            return {"status": response.status if response else None}

        if action.type == BrowserActionType.CLICK:
            if not action.selector:
                raise ValueError("Click action requires selector.")
            await page.locator(action.selector).click(timeout=timeout_ms)
            return {"selector": action.selector}

        if action.type == BrowserActionType.TYPE_TEXT:
            if not action.selector:
                raise ValueError("Type text action requires selector.")
            if action.text is None:
                raise ValueError("Type text action requires text.")
            await page.locator(action.selector).fill(action.text, timeout=timeout_ms)
            return {"selector": action.selector, "text_length": len(action.text)}

        if action.type == BrowserActionType.WAIT_FOR_SELECTOR:
            if not action.selector:
                raise ValueError("Wait action requires selector.")
            await page.locator(action.selector).wait_for(timeout=timeout_ms)
            return {"selector": action.selector}

        if action.type == BrowserActionType.EXTRACT_TEXT:
            selector = action.selector or "body"
            text = await page.locator(selector).inner_text(timeout=timeout_ms)
            return {"selector": selector, "text": text}

        if action.type == BrowserActionType.SCREENSHOT:
            screenshot_path = self._build_screenshot_path(action.screenshot_name)
            await page.screenshot(path=str(screenshot_path), full_page=True)
            return {"screenshot_path": str(screenshot_path)}

        if action.type == BrowserActionType.GET_STATE:
            return {"url": page.url, "title": await page.title()}

        raise ValueError(f"Unsupported browser action: {action.type}")

    def _timeout_ms(self, action: BrowserAction) -> float:
        seconds = action.timeout_seconds or self.session.config.action_timeout_seconds
        return seconds * 1000

    def _build_screenshot_path(self, screenshot_name: str | None) -> Path:
        name = screenshot_name or "screenshot.png"
        if not name.endswith(".png"):
            name = f"{name}.png"
        safe_name = "".join(char if char.isalnum() or char in "-_." else "_" for char in name)
        run_dir = self.session.config.screenshot_dir / str(self.session.run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir / safe_name

    def _failure(self, action: BrowserAction, error: str, retryable: bool) -> BrowserActionResult:
        return BrowserActionResult(
            ok=False,
            action_type=action.type,
            error=error,
            retryable=retryable,
        )

