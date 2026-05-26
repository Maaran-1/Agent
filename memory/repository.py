from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database import MemoryRecord

from .models import LongTermMemory, MemoryType


class MemoryRepository:
    """SQLite-backed repository for long-term memories."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, memory: LongTermMemory) -> LongTermMemory:
        record = MemoryRecord(
            id=str(memory.id),
            type=memory.type.value,
            content=memory.content,
            source=memory.source,
            confidence=memory.confidence,
            metadata_=memory.metadata,
            created_at=memory.created_at,
        )
        self.session.add(record)
        await self.session.flush()
        return memory

    async def create_run_summary(
        self,
        content: str,
        source: str,
        confidence: float = 0.8,
        metadata: dict | None = None,
    ) -> LongTermMemory:
        memory = LongTermMemory(
            type=MemoryType.RUN_SUMMARY,
            content=content,
            source=source,
            confidence=confidence,
            metadata=metadata or {},
        )
        return await self.create(memory)

    async def list(
        self,
        memory_type: MemoryType | None = None,
        source: str | None = None,
        min_confidence: float | None = None,
        limit: int = 50,
    ) -> list[LongTermMemory]:
        statement = select(MemoryRecord).order_by(MemoryRecord.created_at.desc()).limit(limit)
        if memory_type is not None:
            statement = statement.where(MemoryRecord.type == memory_type.value)
        if source is not None:
            statement = statement.where(MemoryRecord.source == source)
        if min_confidence is not None:
            statement = statement.where(MemoryRecord.confidence >= min_confidence)

        records = (await self.session.scalars(statement)).all()
        return [self._to_model(record) for record in records]

    async def search_text(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        min_confidence: float = 0.0,
        limit: int = 10,
    ) -> list[LongTermMemory]:
        normalized_query = query.strip().lower()
        if not normalized_query:
            return await self.list(
                memory_type=memory_type,
                min_confidence=min_confidence,
                limit=limit,
            )

        statement = (
            select(MemoryRecord)
            .where(MemoryRecord.confidence >= min_confidence)
            .order_by(MemoryRecord.confidence.desc(), MemoryRecord.created_at.desc())
            .limit(limit * 5)
        )
        if memory_type is not None:
            statement = statement.where(MemoryRecord.type == memory_type.value)

        records = (await self.session.scalars(statement)).all()
        scored = [
            (self._score(normalized_query, record), record)
            for record in records
        ]
        matches = [
            record
            for score, record in sorted(scored, key=lambda item: item[0], reverse=True)
            if score > 0
        ]
        return [self._to_model(record) for record in matches[:limit]]

    async def delete(self, memory_id: UUID) -> bool:
        result = await self.session.execute(
            delete(MemoryRecord).where(MemoryRecord.id == str(memory_id))
        )
        return bool(result.rowcount)

    def _to_model(self, record: MemoryRecord) -> LongTermMemory:
        return LongTermMemory(
            id=UUID(record.id),
            type=MemoryType(record.type),
            content=record.content,
            source=record.source,
            confidence=record.confidence,
            metadata=record.metadata_ or {},
            created_at=record.created_at,
        )

    def _score(self, normalized_query: str, record: MemoryRecord) -> int:
        haystack = f"{record.content} {record.source}".lower()
        query_terms = set(normalized_query.split())
        return sum(1 for term in query_terms if term in haystack)


class MemoryRetrievalPolicy:
    """Basic text retrieval policy with an embeddings-ready boundary."""

    def __init__(
        self,
        repository: MemoryRepository,
        min_confidence: float = 0.5,
        limit: int = 5,
    ) -> None:
        self.repository = repository
        self.min_confidence = min_confidence
        self.limit = limit

    async def retrieve_for_task(
        self,
        task: str,
        memory_types: Sequence[MemoryType] | None = None,
    ) -> list[LongTermMemory]:
        if memory_types is None:
            return await self.repository.search_text(
                task,
                min_confidence=self.min_confidence,
                limit=self.limit,
            )

        results: list[LongTermMemory] = []
        for memory_type in memory_types:
            results.extend(
                await self.repository.search_text(
                    task,
                    memory_type=memory_type,
                    min_confidence=self.min_confidence,
                    limit=self.limit,
                )
            )

        deduped: dict[UUID, LongTermMemory] = {memory.id: memory for memory in results}
        return sorted(
            deduped.values(),
            key=lambda memory: (memory.confidence, memory.created_at),
            reverse=True,
        )[: self.limit]
