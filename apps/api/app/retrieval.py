from __future__ import annotations

import uuid
from typing import List, Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import SourceText, TextEmbedding


async def search_by_embedding(
    session: AsyncSession,
    *,
    query_embedding: List[float],
    tradition: str,
    chunk_types: Optional[Sequence[str]] = None,
    top_k: int = 12,
    embedding_model: str,
    embedding_dim: int,
    embedding_version: str,
) -> List[SourceText]:
    stmt = (
        select(SourceText)
        .join(TextEmbedding, TextEmbedding.source_text_id == SourceText.id)
        .where(
            SourceText.tradition == tradition,
            SourceText.is_active.is_(True),
            TextEmbedding.embedding_model == embedding_model,
            TextEmbedding.embedding_dim == embedding_dim,
            TextEmbedding.embedding_version == embedding_version,
        )
    )
    if chunk_types:
        stmt = stmt.where(SourceText.chunk_type.in_(list(chunk_types)))
    stmt = stmt.order_by(TextEmbedding.embedding.l2_distance(query_embedding)).limit(top_k)
    res = await session.execute(stmt)
    return list(res.scalars().all())


async def get_texts_by_ids(session: AsyncSession, ids: Sequence[uuid.UUID]) -> List[SourceText]:
    if not ids:
        return []
    stmt = select(SourceText).where(SourceText.id.in_(list(ids)))
    res = await session.execute(stmt)
    rows = list(res.scalars().all())
    by_id = {r.id: r for r in rows}
    return [by_id[i] for i in ids if i in by_id]
