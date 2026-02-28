from __future__ import annotations

import math
from typing import List, Optional

from .settings import settings
from .openrouter_client import OpenRouterClient


def _l2_norm(vec: List[float]) -> float:
    return math.sqrt(sum((x * x) for x in vec))


def normalize(vec: List[float]) -> List[float]:
    n = _l2_norm(vec)
    if n == 0:
        return vec
    return [x / n for x in vec]


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a batch of texts and return **normalized** vectors."""
    cleaned = [t.strip() for t in texts]
    async with OpenRouterClient() as orc:
        embs = await orc.embeddings(
            model=settings.openrouter_embed_model,
            inputs=cleaned,
            dimensions=settings.openrouter_embed_dimensions,
        )
    return [normalize(e) for e in embs]


async def embed_text(text: str) -> List[float]:
    return (await embed_texts([text]))[0]
