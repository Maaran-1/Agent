from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from configs.settings import Settings
from workflows.repository import WorkflowRepository
from workflows.service import WorkflowService


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory
    async with session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_workflow_service(session: AsyncSession) -> WorkflowService:
    return WorkflowService(WorkflowRepository(session))

