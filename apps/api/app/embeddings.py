from __future__ import annotations

from typing import List

import httpx

from .settings import settings


async def embed_text(text: str) -> List[float]:
    vecs = await embed_texts([text])
    return vecs[0]


async def embed_texts(texts: List[str]) -> List[List[float]]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    url = f"{settings.openrouter_base_url.rstrip('/')}/embeddings"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_title:
        headers["X-Title"] = settings.openrouter_app_title
    body: dict = {
        "model": settings.openrouter_embed_model,
        "input": texts,
    }
    if settings.openrouter_embed_dimensions:
        body["dimensions"] = settings.openrouter_embed_dimensions
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(url, headers=headers, json=body)
        r.raise_for_status()
        data = r.json()
    out: List[List[float]] = []
    for item in data["data"]:
        out.append(item["embedding"])
    return out
