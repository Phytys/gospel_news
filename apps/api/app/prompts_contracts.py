"""Logical JSON contracts for LLM outputs (validated with Pydantic)."""

from __future__ import annotations

from typing import List, Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


RelationLabel = Literal["Resonates with", "Deepens", "Contrasts with", "Grounds"]


class AskRelationItem(BaseModel):
    id: str
    relation_label: RelationLabel


class AskLLMOutput(BaseModel):
    selected_canonical_ids: List[str] = Field(..., min_length=2, max_length=2)
    selected_thomas_id: str
    relations: List[AskRelationItem] = Field(..., min_length=3, max_length=3)
    theme_labels: List[str] = Field(default_factory=list)
    interpretation_text: str
    plain_reading_text: str
    deeper_reading_text: str
    why_matched_text: str
    tension_text: Optional[str] = None
    reflection_questions: List[str] = Field(..., min_length=3, max_length=3)
    confidence_notes: Optional[str] = None


class DailyLLMOutput(BaseModel):
    theme_label: str
    selected_canonical_id: str
    selected_thomas_id: str
    daily_rationale_text: str
    interpretation_text: str
    plain_reading_text: str
    deeper_reading_text: str
    why_matched_text: str
    tension_text: Optional[str] = None
    reflection_questions: List[str] = Field(..., min_length=3, max_length=3)


def parse_uuid_list(ids: List[str]) -> List[UUID]:
    return [UUID(x) for x in ids]


def validate_ids_in_pool(selected: List[str], pool: set[str]) -> None:
    for sid in selected:
        if sid not in pool:
            raise ValueError(f"ID not in candidate pool: {sid}")
