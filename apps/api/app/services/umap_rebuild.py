"""Offline UMAP projection for map_points (uses embeddings from text_embeddings).

Pipeline (all computed from data — no hand-waved theme labels):
1. Stack embedding vectors for the active model/version.
2. UMAP (cosine) → 2D coordinates (x, y): nearby points = closer meaning in embedding space.
3. KMeans on those 2D coordinates → region id + label "Region N" for coloring/tooltips
   (partitions the *visible* layout; not a second semantic claim beyond UMAP).
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np
from sklearn.cluster import KMeans
from sqlalchemy import delete, select
from umap import UMAP

from ..db import AsyncSessionLocal, init_db_schema
from ..models import MapPoint, SourceText, TextEmbedding
from ..settings import settings


def _kmeans_regions(xy: np.ndarray) -> np.ndarray:
    """Cluster the UMAP plane so map colors match spatial groupings (real algorithm, not a label list)."""
    n = len(xy)
    # Roughly one region per few hundred points, capped (tune as library grows).
    k = min(24, max(3, n // 200))
    k = min(k, max(2, n - 1))
    model = KMeans(n_clusters=k, random_state=42, n_init=10)
    return model.fit_predict(xy)


async def run_rebuild_umap() -> int:
    await init_db_schema()
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(SourceText, TextEmbedding)
            .join(TextEmbedding, TextEmbedding.source_text_id == SourceText.id)
            .where(
                TextEmbedding.embedding_model == settings.openrouter_embed_model,
                TextEmbedding.embedding_dim == settings.openrouter_embed_dimensions,
                TextEmbedding.embedding_version == settings.embedding_version,
            )
        )
        pairs: List[Tuple[SourceText, TextEmbedding]] = list(res.all())
        if len(pairs) < 10:
            raise RuntimeError("Need at least 10 embedded texts for UMAP")

        ids = [st.id for st, _ in pairs]
        mat = np.array([te.embedding for _, te in pairs], dtype=np.float32)

        n_neighbors = min(15, max(2, len(mat) - 1))
        reducer = UMAP(n_neighbors=n_neighbors, min_dist=0.1, metric="cosine", random_state=42)
        xy = reducer.fit_transform(mat)

        region_labels = _kmeans_regions(xy)

        await session.execute(delete(MapPoint).where(MapPoint.projection_name == "umap_v1"))
        await session.commit()

        for i, sid in enumerate(ids):
            rid = int(region_labels[i])
            session.add(
                MapPoint(
                    source_text_id=sid,
                    projection_name="umap_v1",
                    x=float(xy[i, 0]),
                    y=float(xy[i, 1]),
                    cluster_id=str(rid),
                    cluster_label=f"Region {rid + 1}",
                )
            )
        await session.commit()
        return len(ids)
