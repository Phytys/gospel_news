from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from .settings import settings


class OpenRouterClient:
    def __init__(self) -> None:
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OpenRouterClient":
        self._client = httpx.AsyncClient(timeout=120.0)
        return self

    async def __aexit__(self, *args: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def chat(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 800,
        temperature: float = 0.35,
    ) -> Dict[str, Any]:
        if not settings.openrouter_api_key:
            raise RuntimeError("OPENROUTER_API_KEY is not set")
        assert self._client is not None
        url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "Content-Type": "application/json",
        }
        if settings.openrouter_site_url:
            headers["HTTP-Referer"] = settings.openrouter_site_url
        if settings.openrouter_app_title:
            headers["X-Title"] = settings.openrouter_app_title
        body = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        r = await self._client.post(url, headers=headers, json=body)
        r.raise_for_status()
        return r.json()
