from __future__ import annotations

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from typing import Any, Dict, List, Optional

from .settings import settings


class OpenRouterError(RuntimeError):
    pass


def _default_headers() -> Dict[str, str]:
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    # Optional headers recommended by OpenRouter for attribution / discoverability
    if settings.openrouter_site_url:
        headers["HTTP-Referer"] = settings.openrouter_site_url
    if settings.openrouter_app_title:
        headers["X-OpenRouter-Title"] = settings.openrouter_app_title
    return headers


class OpenRouterClient:
    def __init__(self) -> None:
        self.base_url = settings.openrouter_base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "OpenRouterClient":
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client:
            await self._client.aclose()

    @property
    def client(self) -> httpx.AsyncClient:
        if not self._client:
            raise RuntimeError("OpenRouterClient must be used as an async context manager")
        return self._client

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.8, min=1, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.ReadTimeout)),
    )
    async def chat(self, *, model: str, messages: List[Dict[str, Any]], max_tokens: int = 600, temperature: float = 0.4) -> Dict[str, Any]:
        url = f"{self.base_url}/chat/completions"
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        resp = await self.client.post(url, headers=_default_headers(), json=payload)
        if resp.status_code >= 400:
            raise OpenRouterError(f"OpenRouter chat error {resp.status_code}: {resp.text[:500]}")
        return resp.json()

    @retry(
        reraise=True,
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=0.8, min=1, max=10),
        retry=retry_if_exception_type((httpx.TransportError, httpx.ReadTimeout)),
    )
    async def embeddings(
        self,
        *,
        model: str,
        inputs: List[str],
        dimensions: Optional[int] = None,
        encoding_format: str = "float",
    ) -> List[List[float]]:
        url = f"{self.base_url}/embeddings"
        payload: Dict[str, Any] = {
            "model": model,
            "input": inputs,
            "encoding_format": encoding_format,
        }
        if dimensions is not None:
            payload["dimensions"] = int(dimensions)

        resp = await self.client.post(url, headers=_default_headers(), json=payload)
        if resp.status_code >= 400:
            raise OpenRouterError(f"OpenRouter embeddings error {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        items = data.get("data", [])
        embeddings: List[List[float]] = []
        for item in items:
            emb = item.get("embedding")
            if not isinstance(emb, list):
                raise OpenRouterError("Malformed embeddings response")
            embeddings.append([float(x) for x in emb])
        return embeddings
