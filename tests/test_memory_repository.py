from pathlib import Path

import pytest

from backend.db_session import create_engine, create_session_factory, initialize_database, session_scope
from configs.settings import Settings
from memory.models import LongTermMemory, MemoryType
from memory.repository import MemoryRepository, MemoryRetrievalPolicy


@pytest.fixture
async def memory_repository(tmp_path: Path):
    settings = Settings(sqlite_path=tmp_path / "test.sqlite3")
    engine = create_engine(settings)
    await initialize_database(engine)
    session_factory = create_session_factory(engine)

    async with session_scope(session_factory) as session:
        yield MemoryRepository(session)

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_list_memory(memory_repository: MemoryRepository) -> None:
    memory = LongTermMemory(
        type=MemoryType.DOMAIN_NOTE,
        content="Search pages need an explicit wait after submit.",
        source="test",
        confidence=0.9,
    )

    await memory_repository.create(memory)
    memories = await memory_repository.list()

    assert len(memories) == 1
    assert memories[0].content == memory.content
    assert memories[0].type == MemoryType.DOMAIN_NOTE


@pytest.mark.asyncio
async def test_filters_by_type_source_and_confidence(memory_repository: MemoryRepository) -> None:
    await memory_repository.create(
        LongTermMemory(
            type=MemoryType.TASK_PATTERN,
            content="Use login recovery before retrying checkout.",
            source="agent",
            confidence=0.95,
        )
    )
    await memory_repository.create(
        LongTermMemory(
            type=MemoryType.TOOL_LESSON,
            content="Click failed because selector was stale.",
            source="browser",
            confidence=0.4,
        )
    )

    memories = await memory_repository.list(
        memory_type=MemoryType.TASK_PATTERN,
        source="agent",
        min_confidence=0.8,
    )

    assert len(memories) == 1
    assert memories[0].source == "agent"


@pytest.mark.asyncio
async def test_search_text_returns_relevant_memories(memory_repository: MemoryRepository) -> None:
    await memory_repository.create(
        LongTermMemory(
            type=MemoryType.DOMAIN_NOTE,
            content="Invoices can be downloaded from the billing page.",
            source="agent",
            confidence=0.85,
        )
    )
    await memory_repository.create(
        LongTermMemory(
            type=MemoryType.DOMAIN_NOTE,
            content="Profile avatars require image upload validation.",
            source="agent",
            confidence=0.9,
        )
    )

    memories = await memory_repository.search_text("download invoice billing")

    assert len(memories) == 1
    assert "Invoices" in memories[0].content


@pytest.mark.asyncio
async def test_retrieval_policy_applies_confidence_threshold(
    memory_repository: MemoryRepository,
) -> None:
    await memory_repository.create(
        LongTermMemory(
            type=MemoryType.TASK_PATTERN,
            content="When searching docs, open the API reference first.",
            source="agent",
            confidence=0.95,
        )
    )
    await memory_repository.create(
        LongTermMemory(
            type=MemoryType.TASK_PATTERN,
            content="Docs search sometimes mentions outdated snippets.",
            source="agent",
            confidence=0.2,
        )
    )

    policy = MemoryRetrievalPolicy(memory_repository, min_confidence=0.8)
    memories = await policy.retrieve_for_task(
        "search docs api reference",
        memory_types=[MemoryType.TASK_PATTERN],
    )

    assert len(memories) == 1
    assert memories[0].confidence == 0.95


@pytest.mark.asyncio
async def test_delete_memory(memory_repository: MemoryRepository) -> None:
    memory = await memory_repository.create_run_summary(
        content="Run completed after one browser retry.",
        source="run:test",
    )

    deleted = await memory_repository.delete(memory.id)
    memories = await memory_repository.list()

    assert deleted is True
    assert memories == []

