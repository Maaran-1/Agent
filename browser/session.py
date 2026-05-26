from pathlib import Path
from types import TracebackType
from uuid import UUID

from configs.settings import Settings

from .exceptions import BrowserRecoveryError, BrowserSessionClosedError
from .models import BrowserRuntimeConfig, BrowserViewport


class BrowserSession:
    """Owns one isolated Playwright browser context for a single agent run."""

    def __init__(self, run_id: UUID, config: BrowserRuntimeConfig) -> None:
        self.run_id = run_id
        self.config = config
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    @property
    def page(self):
        if self._page is None:
            raise BrowserSessionClosedError("Browser session is not started.")
        return self._page

    @property
    def is_started(self) -> bool:
        return self._page is not None

    async def start(self) -> None:
        from playwright.async_api import async_playwright

        if self.is_started:
            return

        self.config.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = await async_playwright().start()
        launch_kwargs = {
            "headless": self.config.headless,
            "slow_mo": self.config.slow_mo_ms,
        }
        if self.config.browser_channel:
            launch_kwargs["channel"] = self.config.browser_channel

        self._browser = await self._playwright.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context(
            viewport={
                "width": self.config.viewport.width,
                "height": self.config.viewport.height,
            }
        )
        self._context.set_default_timeout(self.config.action_timeout_seconds * 1000)
        self._page = await self._context.new_page()

    async def close(self) -> None:
        page = self._page
        context = self._context
        browser = self._browser
        playwright = self._playwright
        self._page = None
        self._context = None
        self._browser = None
        self._playwright = None

        if page is not None and not page.is_closed():
            await page.close()
        if context is not None:
            await context.close()
        if browser is not None:
            await browser.close()
        if playwright is not None:
            await playwright.stop()

    async def recover(self) -> None:
        try:
            await self.close()
            await self.start()
        except Exception as exc:  # pragma: no cover - defensive boundary
            raise BrowserRecoveryError("Could not recover browser session.") from exc

    async def __aenter__(self) -> "BrowserSession":
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()


class BrowserSessionManager:
    """Creates isolated browser sessions from application settings."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_config(self) -> BrowserRuntimeConfig:
        return BrowserRuntimeConfig(
            headless=self.settings.browser_headless,
            viewport=BrowserViewport(),
            action_timeout_seconds=self.settings.browser_action_timeout_seconds,
            screenshot_dir=Path(self.settings.logs_dir) / "screenshots",
        )

    def create_session(self, run_id: UUID) -> BrowserSession:
        return BrowserSession(run_id=run_id, config=self.build_config())

