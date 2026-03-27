from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, Dict, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .db import init_db_schema
from .routers import v1
from .settings import settings

logger = logging.getLogger(__name__)


async def _ensure_daily_background() -> None:
    """After deploy/restart, create today's daily if missing (complements worker cron)."""
    await asyncio.sleep(2)
    if not settings.ensure_daily_on_api_startup:
        return
    from .services.daily_service import ensure_today_daily_if_missing

    await ensure_today_daily_if_missing()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db_schema()
    asyncio.create_task(_ensure_daily_background())
    yield


app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1.router, prefix=f"{settings.api_v1_prefix}")


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "env": settings.app_env}
