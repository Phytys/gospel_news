from __future__ import annotations

import orjson
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import DailyDigest, DigestEntry, NewsItem, ScriptureChunk
from .settings import settings
from .news import load_sources, fetch_rss_candidates, extract_article_text, infer_outlet
from .embeddings import embed_text
from .retrieval import search_scripture
from .openrouter_client import OpenRouterClient
from .prompts import build_digest_messages


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _safe_json_loads(s: str) -> Dict[str, Any]:
    s = s.strip()
    try:
        return orjson.loads(s)
    except Exception:
        # Try to salvage first JSON object in the text
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            return orjson.loads(s[start : end + 1])
        raise


def _candidate_payload(rows: List[ScriptureChunk], max_chars: int = 700) -> List[Dict[str, Any]]:
    out = []
    for r in rows:
        txt = r.text.strip()
        if len(txt) > max_chars:
            txt = txt[:max_chars].rsplit(" ", 1)[0] + "…"
        out.append({"ref": r.ref, "doc": r.doc, "text": txt})
    return out


async def _get_or_create_digest(session: AsyncSession, digest_date: date) -> DailyDigest:
    res = await session.execute(
        select(DailyDigest)
        .where(DailyDigest.digest_date == digest_date)
        .options(selectinload(DailyDigest.entries))
    )
    digest = res.scalars().first()
    if digest:
        return digest
    digest = DailyDigest(digest_date=digest_date)
    session.add(digest)
    await session.commit()
    await session.refresh(digest)
    return digest


async def generate_daily_digest(session: AsyncSession, digest_date: Optional[date] = None) -> DailyDigest:
    digest_date = digest_date or date.today()

    # Ensure scripture exists
    res = await session.execute(select(ScriptureChunk.id).limit(1))
    if res.scalar() is None:
        raise RuntimeError("No scripture chunks found. Run: python -m app.scripts.ingest_scripture")

    digest = await _get_or_create_digest(session, digest_date)

    existing_ranks = {e.rank for e in digest.entries}
    next_rank = 1
    while next_rank in existing_ranks:
        next_rank += 1

    if len(existing_ranks) >= settings.stories_per_day:
        return digest

    # Pull RSS candidates
    sources = load_sources(settings.rss_sources_file)
    candidates = fetch_rss_candidates(sources, per_source=15)

    # Insert or reuse news items
    new_items: List[NewsItem] = []
    for c in candidates:
        if len(new_items) >= settings.stories_per_day * 4:
            break

        # already in DB?
        existing = await session.execute(select(NewsItem).where(NewsItem.url == c.url))
        if existing.scalars().first():
            continue

        ni = NewsItem(
            title=c.title,
            url=c.url,
            source=c.source,
            published_at=c.published_at,
            excerpt=c.excerpt,
        )
        session.add(ni)
        new_items.append(ni)

    if new_items:
        await session.commit()

    # Re-query the latest items (including potentially previously fetched ones)
    # We prefer recent news
    res = await session.execute(
        select(NewsItem).order_by((NewsItem.published_at.desc().nullslast()), NewsItem.fetched_at.desc()).limit(50)
    )
    recent_items = list(res.scalars().all())

    # Fill digest entries
    for item in recent_items:
        if len(existing_ranks) >= settings.stories_per_day:
            break

        # Skip if this news item already used today
        used = await session.execute(
            select(DigestEntry).where(DigestEntry.digest_id == digest.id, DigestEntry.news_item_id == item.id)
        )
        if used.scalars().first():
            continue

        # Extract article text if missing
        article_text = item.article_text
        if not article_text:
            extracted = extract_article_text(item.url)
            if extracted:
                article_text = extracted
            else:
                # fallback to title + excerpt only
                article_text = (item.excerpt or "")
            item.article_text = article_text
            await session.commit()

        # Build embedding for retrieval
        emb = item.embedding
        if emb is None:
            # Use a compact but meaningful text for embedding
            embed_input = f"{item.title}\n\n{article_text or ''}"
            emb = await embed_text(embed_input[:8000])
            item.embedding = emb
            item.embedding_model = settings.openrouter_embed_model
            item.embedding_dimensions = settings.openrouter_embed_dimensions
            await session.commit()

        # Retrieve candidates
        canonical = await search_scripture(
            session,
            query_embedding=emb,
            source="canonical",
            chunk_kind="passage",
            top_k=settings.canonical_top_k,
            embedding_model=settings.openrouter_embed_model,
            embedding_dimensions=settings.openrouter_embed_dimensions,
        )
        thomas = await search_scripture(
            session,
            query_embedding=emb,
            source="thomas",
            chunk_kind="saying",
            top_k=settings.thomas_top_k,
            embedding_model=settings.openrouter_embed_model,
            embedding_dimensions=settings.openrouter_embed_dimensions,
        )

        if not canonical:
            canonical = await search_scripture(
                session,
                query_embedding=emb,
                source="canonical",
                chunk_kind=None,
                top_k=settings.canonical_top_k,
                embedding_model=settings.openrouter_embed_model,
                embedding_dimensions=settings.openrouter_embed_dimensions,
            )
        if not thomas:
            thomas = await search_scripture(
                session,
                query_embedding=emb,
                source="thomas",
                chunk_kind=None,
                top_k=settings.thomas_top_k,
                embedding_model=settings.openrouter_embed_model,
                embedding_dimensions=settings.openrouter_embed_dimensions,
            )

        canonical_payload = _candidate_payload(canonical)
        thomas_payload = _candidate_payload(thomas)

        # LLM call: summary + selection + interpretation + questions
        outlet = infer_outlet(item.url)
        published_iso = (item.published_at or item.fetched_at).astimezone(timezone.utc).isoformat()

        messages = build_digest_messages(
            title=item.title,
            outlet=outlet,
            url=item.url,
            published_iso=published_iso,
            article_text=(article_text or "")[:9000],
            canonical_candidates=canonical_payload,
            thomas_candidates=thomas_payload,
        )

        async with OpenRouterClient() as orc:
            resp = await orc.chat(
                model=settings.openrouter_chat_model,
                messages=messages,
                max_tokens=750,
                temperature=0.35,
            )
        content = resp["choices"][0]["message"]["content"]
        data = _safe_json_loads(content)

        # Validate refs are from candidates; if not, hard fallback
        canonical_refs = [r["ref"] for r in canonical_payload]
        thomas_refs = [r["ref"] for r in thomas_payload]

        gospel_refs = [r for r in data.get("gospel_refs", []) if r in canonical_refs]
        if not gospel_refs:
            gospel_refs = canonical_refs[:1] if canonical_refs else []

        thomas_ref = data.get("thomas_ref")
        if thomas_ref not in thomas_refs and thomas_refs:
            thomas_ref = thomas_refs[0]

        summary = str(data.get("summary", "")).strip()
        themes = data.get("themes", [])
        if isinstance(themes, list):
            themes_obj: Dict[str, Any] = {"themes": [str(x) for x in themes][:10]}
        else:
            themes_obj = {"themes": []}

        interpretation = str(data.get("interpretation", "")).strip()
        questions = data.get("questions", [])
        if not isinstance(questions, list):
            questions = []
        questions = [str(q).strip() for q in questions if str(q).strip()][:5]
        if len(questions) < 2:
            questions = [
                "What stands out as most human in this situation?",
                "Where do you notice fear, and where do you notice courage?",
                "What kind of truth would be hard to admit here?",
            ]

        entry = DigestEntry(
            digest_id=digest.id,
            news_item_id=item.id,
            rank=next_rank,
            summary=summary,
            themes=themes_obj,
            gospel_refs=gospel_refs,
            thomas_ref=str(thomas_ref or ""),
            interpretation=interpretation,
            questions=questions,
            generation_meta={
                "openrouter_model": resp.get("model"),
                "usage": resp.get("usage"),
                "generated_at": _utcnow().isoformat(),
            },
        )
        session.add(entry)
        await session.commit()

        existing_ranks.add(next_rank)
        next_rank += 1

    # Refresh digest with entries
    res = await session.execute(
        select(DailyDigest)
        .where(DailyDigest.id == digest.id)
        .options(selectinload(DailyDigest.entries).selectinload(DigestEntry.news_item))
    )
    return res.scalars().first()
