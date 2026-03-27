from __future__ import annotations

import orjson
import uuid
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..embeddings import embed_text
from ..models import SourceText, UserSessionAsk
from ..openrouter_client import OpenRouterClient
from ..prompts_contracts import AskLLMOutput, parse_uuid_list, validate_ids_in_pool
from ..prompts_messages import ASK_SYSTEM, build_ask_user_message
from ..retrieval import get_texts_by_ids, search_by_embedding
from ..settings import settings


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


async def run_ask(
    session: AsyncSession,
    *,
    text: str,
    save_prompt: bool,
) -> Dict[str, Any]:
    if len(text) > settings.ask_max_input_chars:
        raise ValueError("Input too long")

    q_emb = await embed_text(text)

    canonical = await search_by_embedding(
        session,
        query_embedding=q_emb,
        tradition="canonical",
        chunk_types=("passage",),
        top_k=settings.ask_canonical_candidates,
        embedding_model=settings.openrouter_embed_model,
        embedding_dim=settings.openrouter_embed_dimensions,
        embedding_version=settings.embedding_version,
    )
    thomas = await search_by_embedding(
        session,
        query_embedding=q_emb,
        tradition="thomas",
        chunk_types=("saying",),
        top_k=settings.ask_thomas_candidates,
        embedding_model=settings.openrouter_embed_model,
        embedding_dim=settings.openrouter_embed_dimensions,
        embedding_version=settings.embedding_version,
    )
    if not canonical:
        canonical = await search_by_embedding(
            session,
            query_embedding=q_emb,
            tradition="canonical",
            chunk_types=None,
            top_k=settings.ask_canonical_candidates,
            embedding_model=settings.openrouter_embed_model,
            embedding_dim=settings.openrouter_embed_dimensions,
            embedding_version=settings.embedding_version,
        )

    canon_payload = _candidate_payload(canonical)
    thom_payload = _candidate_payload(thomas)
    pool = {c["id"] for c in canon_payload} | {c["id"] for c in thom_payload}

    messages = [
        {"role": "system", "content": ASK_SYSTEM},
        {"role": "user", "content": build_ask_user_message(text, canon_payload, thom_payload)},
    ]

    async with OpenRouterClient() as orc:
        resp = await orc.chat(
            model=settings.openrouter_chat_model,
            messages=messages,
            max_tokens=1200,
            temperature=0.35,
        )
    raw = resp["choices"][0]["message"]["content"]
    data = _safe_json(raw)
    out = AskLLMOutput.model_validate(data)

    validate_ids_in_pool(out.selected_canonical_ids, pool)
    validate_ids_in_pool([out.selected_thomas_id], pool)

    canon_ids = parse_uuid_list(out.selected_canonical_ids)
    thomas_id = uuid.UUID(out.selected_thomas_id)
    rows = await get_texts_by_ids(session, canon_ids + [thomas_id])

    # Persist session
    sess = UserSessionAsk(
        input_text=text if save_prompt else None,
        store_prompt_text=save_prompt,
        input_embedding_model=settings.openrouter_embed_model,
        input_embedding_dim=settings.openrouter_embed_dimensions,
        input_embedding=q_emb,
        selected_canonical_ids=[str(x) for x in out.selected_canonical_ids],
        selected_thomas_id=thomas_id,
        theme_labels=out.theme_labels,
        interpretation_text=out.interpretation_text,
        plain_reading_text=out.plain_reading_text,
        deeper_reading_text=out.deeper_reading_text,
        why_matched_text=out.why_matched_text,
        tension_text=out.tension_text,
        reflection_questions=[str(x) for x in out.reflection_questions],
        relations=[r.model_dump() for r in out.relations],
        is_saved=False,
    )
    session.add(sess)
    await session.commit()
    await session.refresh(sess)

    by_id = {r.id: r for r in rows}
    return {
        "session_id": str(sess.id),
        "canonical": [
            {
                "id": str(r.id),
                "ref_label": r.ref_label,
                "tradition": "canonical",
                "book": r.book,
                "primary_text": r.text,
                "theme_tags": r.theme_tags or [],
            }
            for r in [by_id[i] for i in canon_ids if i in by_id]
        ],
        "thomas": {
            "id": str(by_id[thomas_id].id),
            "ref_label": by_id[thomas_id].ref_label,
            "tradition": "thomas",
            "primary_text": by_id[thomas_id].text,
            "noncanonical_label": "Primary Text — Gospel of Thomas (noncanonical)",
            "theme_tags": by_id[thomas_id].theme_tags or [],
        },
        "relations": [r.model_dump() for r in out.relations],
        "theme_labels": out.theme_labels,
        "interpretation_ai_assisted": out.interpretation_text,
        "plain_reading_ai_assisted": out.plain_reading_text,
        "deeper_reading_ai_assisted": out.deeper_reading_text,
        "why_matched_ai_assisted": out.why_matched_text,
        "tension_ai_assisted": out.tension_text,
        "reflection_questions_ai_assisted": [str(x) for x in out.reflection_questions],
        "confidence_notes": out.confidence_notes,
        "generation_model": resp.get("model"),
    }
