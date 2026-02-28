from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List, Dict, Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .settings import settings
from .db import get_session, init_db_schema, AsyncSessionLocal
from .models import DailyDigest, DigestEntry, ScriptureChunk
from .schemas import DailyDigestOut, DigestEntryOut, AskRequest, AskResponse, ScriptureChunkOut
from .retrieval import get_chunks_by_refs, search_scripture
from .embeddings import embed_text
from .openrouter_client import OpenRouterClient
from .prompts import build_ask_messages
from .digest import generate_daily_digest

SGT = ZoneInfo("Asia/Singapore")

app = FastAPI(title="Gospel Lens MVP", version="0.1.0")

templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.on_event("startup")
async def _startup() -> None:
    await init_db_schema()


def _require_admin(x_admin_token: Optional[str]) -> None:
    if not x_admin_token or x_admin_token != settings.admin_token:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def _load_digest(session: AsyncSession, digest_date: date) -> Optional[DailyDigest]:
    res = await session.execute(
        select(DailyDigest)
        .where(DailyDigest.digest_date == digest_date)
        .options(selectinload(DailyDigest.entries).selectinload(DigestEntry.news_item))
    )
    return res.scalars().first()


def _chunk_to_out(c: ScriptureChunk) -> ScriptureChunkOut:
    return ScriptureChunkOut(
        id=c.id,
        source=c.source,
        doc=c.doc,
        ref=c.ref,
        chunk_kind=c.chunk_kind,
        text=c.text,
        meta=c.meta or {},
    )


async def _digest_to_schema(session: AsyncSession, digest: DailyDigest) -> DailyDigestOut:
    entries_sorted = sorted(digest.entries, key=lambda e: e.rank)

    # Bulk fetch scripture chunks for all refs in this digest
    gospel_refs: List[str] = []
    thomas_refs: List[str] = []
    for e in entries_sorted:
        gospel_refs.extend(e.gospel_refs or [])
        if e.thomas_ref:
            thomas_refs.append(e.thomas_ref)

    # Remove dupes while preserving order
    def uniq(seq: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in seq:
            if x in seen:
                continue
            seen.add(x)
            out.append(x)
        return out

    gospel_refs_u = uniq(gospel_refs)
    thomas_refs_u = uniq(thomas_refs)

    gospel_chunks = await get_chunks_by_refs(session, gospel_refs_u, source="canonical")
    thomas_chunks = await get_chunks_by_refs(session, thomas_refs_u, source="thomas")

    gospel_by_ref = {c.ref: c for c in gospel_chunks}
    thomas_by_ref = {c.ref: c for c in thomas_chunks}

    out_entries: List[DigestEntryOut] = []
    for e in entries_sorted:
        gospel_texts = [_chunk_to_out(gospel_by_ref[r]) for r in (e.gospel_refs or []) if r in gospel_by_ref]
        thomas_text = _chunk_to_out(thomas_by_ref[e.thomas_ref]) if e.thomas_ref in thomas_by_ref else None

        out_entries.append(
            DigestEntryOut(
                id=e.id,
                rank=e.rank,
                summary=e.summary,
                themes=e.themes or {},
                gospel_refs=e.gospel_refs or [],
                thomas_ref=e.thomas_ref,
                gospel_texts=gospel_texts,
                thomas_text=thomas_text,
                interpretation=e.interpretation,
                questions=e.questions or [],
                news_item={
                    "id": e.news_item.id,
                    "title": e.news_item.title,
                    "url": e.news_item.url,
                    "source": e.news_item.source,
                    "published_at": e.news_item.published_at,
                },
                created_at=e.created_at,
            )
        )

    return DailyDigestOut(
        digest_date=digest.digest_date,
        created_at=digest.created_at,
        entries=out_entries,
    )


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    today_sgt = datetime.now(SGT).date()
    digest = await _load_digest(session, today_sgt)
    digest_schema = None
    if digest:
        digest_schema = await _digest_to_schema(session, digest)
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "digest": digest_schema, "today": today_sgt.isoformat()},
    )


@app.get("/digest/{digest_date}", response_class=HTMLResponse)
async def digest_page(digest_date: str, request: Request, session: AsyncSession = Depends(get_session)) -> HTMLResponse:
    try:
        d = date.fromisoformat(digest_date)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    digest = await _load_digest(session, d)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    digest_schema = await _digest_to_schema(session, digest)
    return templates.TemplateResponse("index.html", {"request": request, "digest": digest_schema, "today": d.isoformat()})


@app.get("/api/daily", response_model=DailyDigestOut)
async def api_daily(d: Optional[str] = None, session: AsyncSession = Depends(get_session)) -> DailyDigestOut:
    digest_date = datetime.now(SGT).date()
    if d:
        try:
            digest_date = date.fromisoformat(d)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    digest = await _load_digest(session, digest_date)
    if not digest:
        raise HTTPException(status_code=404, detail="Digest not found")
    return await _digest_to_schema(session, digest)


@app.post("/api/ask", response_model=AskResponse)
async def api_ask(payload: AskRequest, session: AsyncSession = Depends(get_session)) -> AskResponse:
    q = payload.query.strip()
    if not q:
        raise HTTPException(status_code=400, detail="Empty query")

    q_emb = await embed_text(q)

    canonical = await search_scripture(
        session,
        query_embedding=q_emb,
        source="canonical",
        chunk_kind="passage",
        top_k=6,
        embedding_model=settings.openrouter_embed_model,
        embedding_dimensions=settings.openrouter_embed_dimensions,
    )
    thomas = await search_scripture(
        session,
        query_embedding=q_emb,
        source="thomas",
        chunk_kind="saying",
        top_k=6,
        embedding_model=settings.openrouter_embed_model,
        embedding_dimensions=settings.openrouter_embed_dimensions,
    )

    canonical_payload = [{"ref": c.ref, "doc": c.doc, "text": c.text[:600]} for c in canonical]
    thomas_payload = [{"ref": c.ref, "doc": c.doc, "text": c.text[:600]} for c in thomas]

    messages = build_ask_messages(query=q, canonical_matches=canonical_payload, thomas_matches=thomas_payload)

    async with OpenRouterClient() as orc:
        resp = await orc.chat(model=settings.openrouter_chat_model, messages=messages, max_tokens=500, temperature=0.4)

    content = resp["choices"][0]["message"]["content"]
    # Parse JSON (best-effort)
    import orjson

    try:
        data = orjson.loads(content.strip())
    except Exception:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            data = orjson.loads(content[start : end + 1])
        else:
            raise HTTPException(status_code=500, detail="Model returned non-JSON output")

    interpretation = str(data.get("interpretation", "")).strip()
    questions = data.get("questions", [])
    if not isinstance(questions, list):
        questions = []
    questions = [str(x).strip() for x in questions if str(x).strip()][:5]

    return AskResponse(
        query=q,
        gospel_matches=[_chunk_to_out(c) for c in canonical],
        thomas_matches=[_chunk_to_out(c) for c in thomas],
        interpretation=interpretation,
        questions=questions,
    )


@app.post("/api/admin/run-digest")
async def admin_run_digest(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    async with AsyncSessionLocal() as session:
        digest_date = datetime.now(SGT).date()
        digest = await generate_daily_digest(session, digest_date=digest_date)
        return {"ok": True, "digest_date": digest.digest_date.isoformat(), "entries": len(digest.entries)}


@app.post("/api/admin/reingest-scripture")
async def admin_reingest_scripture(
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> Dict[str, Any]:
    _require_admin(x_admin_token)
    # Import inside to keep import time small
    from .scripts.ingest_scripture import main as ingest_main

    await ingest_main()
    return {"ok": True}


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True, "env": settings.app_env}
