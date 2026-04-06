from __future__ import annotations

import json
import logging
import orjson
import uuid
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import AsyncSessionLocal
from ..embeddings import embed_text
from ..models import DailyEntry, DailyHistoryAntiRepeat, SourceText
from ..openrouter_client import OpenRouterClient
from ..prompts_contracts import DailyLLMOutput, validate_ids_in_pool
from ..prompts_messages import DAILY_SYSTEM, build_daily_user_message
from ..retrieval import get_texts_by_ids, search_by_embedding
from ..settings import settings

logger = logging.getLogger(__name__)


def editorial_today() -> date:
    """Calendar 'today' for dailies (generation + default API lookup).

    Uses ``DAILY_TIMEZONE_DEFAULT`` so Docker hosts are not stuck on naive UTC ``date.today()``
    unless you want UTC. Invalid zone names fall back to UTC.
    """
    tz_name = (settings.daily_timezone_default or "UTC").strip() or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        logger.warning("editorial_today: invalid DAILY_TIMEZONE_DEFAULT=%r, using UTC", tz_name)
        tz = ZoneInfo("UTC")
    return datetime.now(tz).date()


def _load_theme_list() -> List[str]:
    config = Path(__file__).resolve().parents[2] / "config" / "daily_themes.json"
    with open(config, encoding="utf-8") as f:
        obj = json.load(f)
    return list(obj["themes"])


def _theme_for_date(d: date) -> str:
    """Editorial theme for `d`: one entry per calendar day (see config/daily_themes.json, typically 366)."""
    themes = _load_theme_list()
    idx = d.timetuple().tm_yday - 1
    if idx >= len(themes):
        idx = idx % len(themes)
    return themes[idx]


def _safe_json(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return orjson.loads(s)
    except Exception:
        start, end = s.find("{"), s.rfind("}")
        if start != -1 and end > -1 and end > start:
            return orjson.loads(s[start : end + 1])
        raise


def _candidate_payload(rows: List[SourceText], max_chars: int = 900) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        txt = r.text.strip()
        if len(txt) > max_chars:
            txt = txt[:max_chars].rsplit(" ", 1)[0] + "…"
        out.append(
            {
                "id": str(r.id),
                "ref_label": r.ref_label,
                "book": r.book,
                "chunk_type": r.chunk_type,
                "theme_tags": r.theme_tags or [],
                "text": txt,
            }
        )
    return out


async def get_daily(
    session: AsyncSession,
    *,
    entry_date: Optional[date] = None,
) -> Optional[DailyEntry]:
    entry_date = entry_date or editorial_today()
    res = await session.execute(select(DailyEntry).where(DailyEntry.entry_date == entry_date, DailyEntry.is_published.is_(True)))
    return res.scalars().first()


async def list_published_daily_summaries(session: AsyncSession) -> List[Dict[str, str]]:
    """Date + theme for each published daily, newest first (for archive UI)."""
    res = await session.execute(
        select(DailyEntry.entry_date, DailyEntry.theme_label)
        .where(DailyEntry.is_published.is_(True))
        .order_by(DailyEntry.entry_date.desc())
    )
    return [{"entry_date": r[0].isoformat(), "theme_label": r[1]} for r in res.all()]


async def generate_daily_for_date(session: AsyncSession, target_date: date, *, replace: bool = False) -> DailyEntry:
    """Generate and persist a daily. If ``replace`` is True, remove an existing row for that date (and history) first."""
    if replace:
        await session.execute(delete(DailyEntry).where(DailyEntry.entry_date == target_date))
        await session.execute(delete(DailyHistoryAntiRepeat).where(DailyHistoryAntiRepeat.entry_date == target_date))
        await session.commit()

    theme = _theme_for_date(target_date)
    theme_emb = await embed_text(theme + " " + theme)

    canonical = await search_by_embedding(
        session,
        query_embedding=theme_emb,
        tradition="canonical",
        chunk_types=("passage",),
        top_k=16,
        embedding_model=settings.openrouter_embed_model,
        embedding_dim=settings.openrouter_embed_dimensions,
        embedding_version=settings.embedding_version,
    )
    thomas = await search_by_embedding(
        session,
        query_embedding=theme_emb,
        tradition="thomas",
        chunk_types=("saying",),
        top_k=12,
        embedding_model=settings.openrouter_embed_model,
        embedding_dim=settings.openrouter_embed_dimensions,
        embedding_version=settings.embedding_version,
    )
    if not canonical or not thomas:
        raise RuntimeError("Insufficient candidates for daily generation")

    canon_payload = _candidate_payload(canonical)
    thom_payload = _candidate_payload(thomas)
    pool = {c["id"] for c in canon_payload} | {c["id"] for c in thom_payload}

    # Recent history
    res = await session.execute(
        select(DailyHistoryAntiRepeat).order_by(DailyHistoryAntiRepeat.entry_date.desc()).limit(14)
    )
    hist = list(res.scalars().all())
    recent_refs = "\n".join(f"{h.entry_date}: {h.canonical_id} / {h.thomas_id}" for h in hist) or "(none)"

    messages = [
        {"role": "system", "content": DAILY_SYSTEM},
        {
            "role": "user",
            "content": build_daily_user_message(theme, canon_payload, thom_payload, recent_refs),
        },
    ]

    async with OpenRouterClient() as orc:
        resp = await orc.chat(
            model=settings.openrouter_chat_model,
            messages=messages,
            max_tokens=1000,
            temperature=0.35,
        )
    raw = resp["choices"][0]["message"]["content"]
    data = _safe_json(raw)
    out = DailyLLMOutput.model_validate(data)

    validate_ids_in_pool([out.selected_canonical_id], pool)
    validate_ids_in_pool([out.selected_thomas_id], pool)

    cid = uuid.UUID(out.selected_canonical_id)
    tid = uuid.UUID(out.selected_thomas_id)

    existing = await session.execute(select(DailyEntry).where(DailyEntry.entry_date == target_date))
    if existing.scalars().first():
        raise ValueError(f"Daily entry already exists for {target_date}")

    entry = DailyEntry(
        entry_date=target_date,
        theme_label=out.theme_label,
        canonical_source_text_id=cid,
        thomas_source_text_id=tid,
        daily_rationale_text=out.daily_rationale_text,
        interpretation_text=out.interpretation_text,
        plain_reading_text=out.plain_reading_text,
        deeper_reading_text=out.deeper_reading_text,
        why_matched_text=out.why_matched_text,
        tension_text=out.tension_text,
        reflection_questions=[str(x) for x in out.reflection_questions],
        generation_model=resp.get("model") or settings.openrouter_chat_model,
        generation_prompt_version=settings.prompt_version,
        is_published=True,
    )
    session.add(entry)
    session.add(
        DailyHistoryAntiRepeat(
            entry_date=target_date,
            canonical_id=cid,
            thomas_id=tid,
        )
    )
    await session.commit()
    await session.refresh(entry)
    return entry


async def ensure_today_daily_if_missing() -> None:
    """If there is no published daily for today, generate one. Idempotent; safe if worker runs in parallel."""
    today = editorial_today()
    async with AsyncSessionLocal() as session:
        if await get_daily(session, entry_date=today):
            return
        try:
            await generate_daily_for_date(session, today)
            logger.info("ensure_today_daily_if_missing: created daily for %s", today)
        except ValueError:
            # Duplicate date (race with worker or another API worker).
            return
        except Exception as e:
            logger.warning(
                "ensure_today_daily_if_missing: could not generate daily for %s: %s",
                today,
                e,
            )
