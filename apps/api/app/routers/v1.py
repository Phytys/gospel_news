from __future__ import annotations

import logging
import uuid
from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..models import DailyEntry, UserSessionAsk
from ..services.ask_service import run_ask
from ..services.daily_service import (
    editorial_today,
    generate_daily_for_date,
    get_daily,
    list_published_daily_summaries,
)
from ..services.map_service import get_node, list_map_points, map_query_point
from ..settings import settings
from ..rate_limit import ask_limiter
from ..text_sanitize import sanitize_source_display

logger = logging.getLogger(__name__)

router = APIRouter()


class AskIn(BaseModel):
    text: str = Field(..., max_length=4000)
    timezone: str = "UTC"
    save_prompt: bool = False


@router.post("/ask")
async def api_ask(payload: AskIn, request: Request, session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    client_ip = request.client.host if request.client else "unknown"
    allowed, wait = ask_limiter.check(client_ip)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Please wait {wait}s.",
            headers={"Retry-After": str(wait)},
        )
    try:
        return await run_ask(session, text=payload.text.strip(), save_prompt=payload.save_prompt)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/daily/archive")
async def api_daily_archive(session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    """List published dailies (date + theme) for browsing past days."""
    entries = await list_published_daily_summaries(session)
    return {"entries": entries}


async def _daily_payload(session: AsyncSession, entry: DailyEntry) -> Dict[str, Any]:
    from ..models import SourceText

    res = await session.execute(
        select(SourceText).where(SourceText.id.in_([entry.canonical_source_text_id, entry.thomas_source_text_id]))
    )
    rows = {r.id: r for r in res.scalars().all()}
    c = rows.get(entry.canonical_source_text_id)
    t = rows.get(entry.thomas_source_text_id)
    return {
        "entry_date": entry.entry_date.isoformat(),
        "theme_label": entry.theme_label,
        "daily_rationale_ai_assisted": entry.daily_rationale_text,
        "canonical": {
            "id": str(c.id),
            "ref_label": c.ref_label,
            "primary_text": sanitize_source_display(c.text),
            "tradition": "canonical",
        }
        if c
        else None,
        "thomas": {
            "id": str(t.id),
            "ref_label": t.ref_label,
            "primary_text": sanitize_source_display(t.text),
            "tradition": "thomas",
            "noncanonical_label": "Primary Text — Gospel of Thomas (noncanonical)",
        }
        if t
        else None,
        "interpretation_ai_assisted": entry.interpretation_text,
        "plain_reading_ai_assisted": entry.plain_reading_text,
        "deeper_reading_ai_assisted": entry.deeper_reading_text,
        "why_matched_ai_assisted": entry.why_matched_text,
        "tension_ai_assisted": entry.tension_text,
        "reflection_questions_ai_assisted": entry.reflection_questions,
        "generation_model": entry.generation_model,
        "generation_prompt_version": entry.generation_prompt_version,
    }


@router.get("/daily")
async def api_daily(
    d: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    digest_date = editorial_today()
    if d:
        try:
            digest_date = date.fromisoformat(d)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date YYYY-MM-DD")
    entry = await get_daily(session, entry_date=digest_date)
    if not entry:
        # Close the "midnight gap": create today or "tomorrow" (editorial) on first read so the new day appears
        # as soon as someone opens Daily, without waiting only on the worker cron.
        et = editorial_today()
        if digest_date == et or digest_date == et + timedelta(days=1):
            try:
                await generate_daily_for_date(session, digest_date)
                logger.info("api_daily: generated missing daily for %s on demand", digest_date)
            except ValueError:
                pass
            except Exception as e:
                logger.warning("api_daily: on-demand generate failed for %s: %s", digest_date, e)
            entry = await get_daily(session, entry_date=digest_date)
    if not entry:
        raise HTTPException(status_code=404, detail="No daily entry for this date")
    return await _daily_payload(session, entry)


@router.get("/map")
async def api_map(
    tradition: Optional[str] = Query(None, description="canonical | thomas | all"),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    t = None if not tradition or tradition == "all" else tradition
    points = await list_map_points(session, tradition=t)
    return {"projection": "umap_v1", "points": points}


@router.get("/map/node/{node_id}")
async def api_map_node(node_id: str, session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    try:
        uid = uuid.UUID(node_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid id")
    node = await get_node(session, uid)
    if not node:
        raise HTTPException(status_code=404, detail="Not found")
    return node


class MapQueryIn(BaseModel):
    text: str = Field(..., max_length=2000)


@router.post("/map/query")
async def api_map_query(payload: MapQueryIn, session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    return await map_query_point(session, payload.text.strip())


@router.post("/save/session/{session_id}")
async def api_save_session(session_id: str, session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    try:
        uid = uuid.UUID(session_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid session id")
    res = await session.execute(select(UserSessionAsk).where(UserSessionAsk.id == uid))
    row = res.scalars().first()
    if not row:
        raise HTTPException(status_code=404, detail="Session not found")
    row.is_saved = True
    await session.commit()
    return {"ok": True, "session_id": session_id}


def _admin(token: Optional[str]) -> None:
    if not token or token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.post("/admin/ingest-texts")
async def admin_ingest(
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _admin(x_admin_token)
    from ..ingest_pipeline import run_ingest

    n = await run_ingest()
    return {"ok": True, "source_texts": n}


@router.post("/admin/generate-daily")
async def admin_gen_daily(
    d: Optional[str] = None,
    replace: bool = Query(False, description="If true, delete existing daily for this date and regenerate"),
    x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    _admin(x_admin_token)
    target = editorial_today()
    if d:
        try:
            target = date.fromisoformat(d)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date")
    try:
        entry = await generate_daily_for_date(session, target, replace=replace)
        return {"ok": True, "entry_date": entry.entry_date.isoformat(), "id": str(entry.id), "replaced": replace}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/admin/rebuild-map")
async def admin_rebuild_map(x_admin_token: Optional[str] = Header(None, alias="X-Admin-Token")) -> Dict[str, Any]:
    _admin(x_admin_token)
    from ..services.umap_rebuild import run_rebuild_umap

    try:
        n = await run_rebuild_umap()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"ok": True, "map_points": n}
