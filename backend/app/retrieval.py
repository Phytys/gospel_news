from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ScriptureChunk


async def search_scripture(
    session: AsyncSession,
    *,
    query_embedding: List[float],
    source: str,
    chunk_kind: Optional[str] = None,
    top_k: int = 10,
    embedding_model: Optional[str] = None,
    embedding_dimensions: Optional[int] = None,
) -> List[ScriptureChunk]:
    stmt = select(ScriptureChunk).where(ScriptureChunk.source == source)

    if chunk_kind:
        stmt = stmt.where(ScriptureChunk.chunk_kind == chunk_kind)

    if embedding_model:
        stmt = stmt.where(ScriptureChunk.embedding_model == embedding_model)

    if embedding_dimensions:
        stmt = stmt.where(ScriptureChunk.embedding_dimensions == embedding_dimensions)

    stmt = stmt.where(ScriptureChunk.embedding.is_not(None))
    # With normalized vectors, L2 distance ranking corresponds to cosine similarity ranking.
    stmt = stmt.order_by(ScriptureChunk.embedding.l2_distance(query_embedding)).limit(top_k)

    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_chunks_by_refs(
    session: AsyncSession, refs: Sequence[str], source: Optional[str] = None
) -> List[ScriptureChunk]:
    if not refs:
        return []
    stmt = select(ScriptureChunk).where(ScriptureChunk.ref.in_(list(refs)))
    if source:
        stmt = stmt.where(ScriptureChunk.source == source)
    res = await session.execute(stmt)
    rows = list(res.scalars().all())
    # Preserve input order if possible
    by_ref = {r.ref: r for r in rows}
    return [by_ref[r] for r in refs if r in by_ref]
