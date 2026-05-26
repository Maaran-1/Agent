import sys
from pathlib import Path

from loguru import logger

from configs.settings import Settings


def configure_logging(settings: Settings) -> None:
    """Configure structured console and file logging."""

    settings.logs_dir.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(
        sys.stderr,
        level=settings.log_level,
        backtrace=False,
        diagnose=settings.environment == "local",
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> "
            "| <level>{level: <8}</level> "
            "| {extra[component]} "
            "| {message}"
        ),
    )
    logger.add(
        Path(settings.logs_dir) / "agent.log",
        level=settings.log_level,
        rotation="10 MB",
        retention="14 days",
        serialize=True,
        enqueue=True,
    )
    logger.configure(extra={"component": "app"})


def get_logger(component: str):
    return logger.bind(component=component)

