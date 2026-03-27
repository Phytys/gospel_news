from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, List, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text as sql_text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class SourceText(Base):
    __tablename__ = "source_texts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tradition: Mapped[str] = mapped_column(String(16), index=True)  # canonical | thomas
    chunk_type: Mapped[str] = mapped_column(String(16), index=True)  # verse | passage | saying
    book: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    chapter_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verse_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chapter_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    verse_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    saying_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    ref_label: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    plain_gloss: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    theme_tags: Mapped[List[Any]] = mapped_column(JSONB, server_default=sql_text("'[]'::jsonb"))
    source_translation: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_key: Mapped[str] = mapped_column(String(512), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("now()"), onupdate=sql_text("now()")
    )

    embeddings: Mapped[List["TextEmbedding"]] = relationship(back_populates="source_text", cascade="all, delete-orphan")
    map_points: Mapped[List["MapPoint"]] = relationship(back_populates="source_text", cascade="all, delete-orphan")


class TextEmbedding(Base):
    __tablename__ = "text_embeddings"
    __table_args__ = (
        UniqueConstraint(
            "source_text_id",
            "embedding_model",
            "embedding_dim",
            "embedding_version",
            name="uq_text_embedding_model_version",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_text_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_texts.id", ondelete="CASCADE"), index=True
    )
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_version: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[List[float]] = mapped_column(Vector, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))

    source_text: Mapped["SourceText"] = relationship(back_populates="embeddings")


class MapPoint(Base):
    __tablename__ = "map_points"
    __table_args__ = (UniqueConstraint("source_text_id", "projection_name", name="uq_map_point_projection"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_text_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_texts.id", ondelete="CASCADE"), index=True
    )
    projection_name: Mapped[str] = mapped_column(String(64), nullable=False, default="umap_v1")
    x: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    y: Mapped[float] = mapped_column(Numeric(20, 10), nullable=False)
    cluster_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    cluster_label: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))

    source_text: Mapped["SourceText"] = relationship(back_populates="map_points")


class DailyEntry(Base):
    __tablename__ = "daily_entries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_date: Mapped[date] = mapped_column(Date, unique=True, nullable=False, index=True)
    theme_label: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    canonical_source_text_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_texts.id"))
    thomas_source_text_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("source_texts.id"))
    daily_rationale_text: Mapped[str] = mapped_column(Text, nullable=False)
    interpretation_text: Mapped[str] = mapped_column(Text, nullable=False)
    plain_reading_text: Mapped[str] = mapped_column(Text, nullable=False)
    deeper_reading_text: Mapped[str] = mapped_column(Text, nullable=False)
    why_matched_text: Mapped[str] = mapped_column(Text, nullable=False)
    tension_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection_questions: Mapped[List[Any]] = mapped_column(JSONB, nullable=False)
    generation_model: Mapped[str] = mapped_column(String(128), nullable=False)
    generation_prompt_version: Mapped[str] = mapped_column(String(64), nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("now()"), onupdate=sql_text("now()")
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(String(256), unique=True, nullable=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    auth_provider: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("now()"), onupdate=sql_text("now()")
    )


class UserSessionAsk(Base):
    __tablename__ = "user_sessions_ask"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    input_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    input_embedding_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    input_embedding_dim: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    input_embedding: Mapped[Optional[List[float]]] = mapped_column(Vector, nullable=True)
    selected_canonical_ids: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    selected_thomas_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    theme_labels: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    interpretation_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    plain_reading_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    deeper_reading_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    why_matched_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tension_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reflection_questions: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    relations: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True)
    is_saved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    store_prompt_text: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=sql_text("now()"), onupdate=sql_text("now()")
    )


class UserNote(Base):
    __tablename__ = "user_notes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    daily_entry_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))


class DailyThemeSignal(Base):
    __tablename__ = "daily_theme_signals"
    __table_args__ = (
        UniqueConstraint("signal_date", "theme_label", "signal_source", name="uq_daily_theme_signal"),
    )

    signal_date: Mapped[date] = mapped_column(Date, primary_key=True)
    theme_label: Mapped[str] = mapped_column(String(128), primary_key=True)
    signal_source: Mapped[str] = mapped_column(String(32), primary_key=True)  # editorial | aggregate_user | fallback_rotation
    weight: Mapped[float] = mapped_column(Numeric(12, 6), nullable=False, default=1.0)


class DailyHistoryAntiRepeat(Base):
    """Tracks recent daily selections for anti-repetition (simplified: dates + ids)."""

    __tablename__ = "daily_selection_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entry_date: Mapped[date] = mapped_column(Date, index=True)
    canonical_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    thomas_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=sql_text("now()"))
