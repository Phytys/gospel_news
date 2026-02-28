from __future__ import annotations

from datetime import datetime, date
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ScriptureChunkOut(BaseModel):
    id: int
    source: str
    doc: str
    ref: str
    chunk_kind: str
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class NewsItemOut(BaseModel):
    id: int
    title: str
    url: str
    source: str
    published_at: Optional[datetime] = None


class DigestEntryOut(BaseModel):
    id: int
    rank: int
    summary: str
    themes: Dict[str, Any] = Field(default_factory=dict)

    gospel_refs: List[str]
    thomas_ref: str

    # Primary Text blocks (resolved from refs)
    gospel_texts: List[ScriptureChunkOut] = Field(default_factory=list)
    thomas_text: Optional[ScriptureChunkOut] = None

    interpretation: str
    questions: List[str] = Field(default_factory=list)

    news_item: NewsItemOut
    created_at: datetime


class DailyDigestOut(BaseModel):
    digest_date: date
    created_at: datetime
    entries: List[DigestEntryOut]


class AskRequest(BaseModel):
    query: str = Field(min_length=2, max_length=2000)


class AskResponse(BaseModel):
    query: str
    gospel_matches: List[ScriptureChunkOut]
    thomas_matches: List[ScriptureChunkOut]
    interpretation: str
    questions: List[str]
