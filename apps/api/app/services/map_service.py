from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..embeddings import embed_text
from ..models import MapPoint, SourceText
from ..retrieval import search_by_embedding
from ..settings import settings


async def list_map_points(session: AsyncSession, tradition: Optional[str] = None) -> List[Dict[str, Any]]:
    stmt = (
        select(MapPoint, SourceText)
        .join(SourceText, SourceText.id == MapPoint.source_text_id)
        .where(MapPoint.projection_name == "umap_v1")
    )
    if tradition:
        stmt = stmt.where(SourceText.tradition == tradition)
    res = await session.execute(stmt)
    out = []
    for mp, st in res.all():
        out.append(
            {
                "id": str(st.id),
                "x": float(mp.x),
                "y": float(mp.y),
                "tradition": st.tradition,
                "book": st.book,
                "ref_label": st.ref_label,
                "chunk_type": st.chunk_type,
                "cluster_id": mp.cluster_id,
                "cluster_label": mp.cluster_label,
                "preview": st.text[:280] + ("…" if len(st.text) > 280 else ""),
            }
        )
    return out


async def get_node(session: AsyncSession, node_id: uuid.UUID) -> Optional[Dict[str, Any]]:
    res = await session.execute(select(SourceText).where(SourceText.id == node_id))
    st = res.scalars().first()
    if not st:
        return None
    mp_res = await session.execute(
        select(MapPoint).where(MapPoint.source_text_id == node_id, MapPoint.projection_name == "umap_v1")
    )
    mp = mp_res.scalars().first()
    return {
        "id": str(st.id),
        "ref_label": st.ref_label,
        "tradition": st.tradition,
        "chunk_type": st.chunk_type,
        "title": st.title,
        "primary_text": st.text,
        "theme_tags": st.theme_tags or [],
        "map": {
            "x": float(mp.x),
            "y": float(mp.y),
            "cluster_id": mp.cluster_id,
            "cluster_label": mp.cluster_label,
        }
        if mp
        else None,
    }


async def map_query_point(session: AsyncSession, text: str) -> Dict[str, Any]:
    """Return nearest neighbors in embedding space + placeholder map coords if UMAP transform unavailable."""
    q_emb = await embed_text(text)
    canonical = await search_by_embedding(
        session,
        query_embedding=q_emb,
        tradition="canonical",
        chunk_types=("passage",),
        top_k=3,
        embedding_model=settings.openrouter_embed_model,
        embedding_dim=settings.openrouter_embed_dimensions,
        embedding_version=settings.embedding_version,
    )
    thomas = await search_by_embedding(
        session,
        query_embedding=q_emb,
        tradition="thomas",
        chunk_types=("saying",),
        top_k=2,
        embedding_model=settings.openrouter_embed_model,
        embedding_dim=settings.openrouter_embed_dimensions,
        embedding_version=settings.embedding_version,
    )
    nearest = []
    for r in canonical + thomas:
        nearest.append({"id": str(r.id), "ref_label": r.ref_label, "tradition": r.tradition})
    return {
        "query_embedding_model": settings.openrouter_embed_model,
        "nearest": nearest,
        "map_projection_note": "Query point UMAP projection requires offline transform; use nearest texts for map context.",
    }
