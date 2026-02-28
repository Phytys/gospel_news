from __future__ import annotations

from datetime import datetime, date
from typing import Optional, List, Dict, Any

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, Integer, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class ScriptureChunk(Base):
    __tablename__ = "scripture_chunks"
    __table_args__ = (
        UniqueConstraint("source", "ref", "chunk_kind", "embedding_model", "embedding_dimensions", name="uq_chunk_model"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 'canonical' | 'thomas'
    source: Mapped[str] = mapped_column(String(32), index=True)

    # 'Matthew' | 'Mark' | 'Luke' | 'John' | 'Thomas'
    doc: Mapped[str] = mapped_column(String(64), index=True)

    # Human reference string. Examples:
    # - "Matthew 5:1-12"
    # - "Thomas 3"
    ref: Mapped[str] = mapped_column(String(128), index=True)

    # 'verse' | 'passage' | 'saying'
    chunk_kind: Mapped[str] = mapped_column(String(32), index=True)

    # Optional extra metadata
    meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    text: Mapped[str] = mapped_column(Text)

    # Embedding
    embedding_model: Mapped[str] = mapped_column(String(128), index=True)
    embedding_dimensions: Mapped[int] = mapped_column(Integer, index=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class NewsItem(Base):
    __tablename__ = "news_items"
    __table_args__ = (UniqueConstraint("url", name="uq_news_url"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(128), index=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # What we fetched / extracted
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    article_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    # Embedding for retrieval (optional)
    embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    embedding_dimensions: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(Vector, nullable=True)

    digest_entries: Mapped[List["DigestEntry"]] = relationship(back_populates="news_item")


class DailyDigest(Base):
    __tablename__ = "daily_digests"
    __table_args__ = (UniqueConstraint("digest_date", name="uq_digest_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    digest_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    entries: Mapped[List["DigestEntry"]] = relationship(back_populates="digest", cascade="all, delete-orphan")


class DigestEntry(Base):
    __tablename__ = "digest_entries"
    __table_args__ = (UniqueConstraint("digest_id", "rank", name="uq_digest_rank"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    digest_id: Mapped[int] = mapped_column(ForeignKey("daily_digests.id", ondelete="CASCADE"), index=True)
    news_item_id: Mapped[int] = mapped_column(ForeignKey("news_items.id", ondelete="CASCADE"), index=True)
    rank: Mapped[int] = mapped_column(Integer, index=True)

    # Interpretation (AI-assisted)
    summary: Mapped[str] = mapped_column(Text)
    themes: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    # Primary Text references (not generated text)
    gospel_refs: Mapped[List[str]] = mapped_column(JSONB, default=list)
    thomas_ref: Mapped[str] = mapped_column(String(64))

    interpretation: Mapped[str] = mapped_column(Text)
    questions: Mapped[List[str]] = mapped_column(JSONB, default=list)

    # Traceability
    generation_meta: Mapped[Dict[str, Any]] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, index=True)

    digest: Mapped["DailyDigest"] = relationship(back_populates="entries")
    news_item: Mapped["NewsItem"] = relationship(back_populates="digest_entries")
