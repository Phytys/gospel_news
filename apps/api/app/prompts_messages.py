from __future__ import annotations

from typing import Any, Dict, List

ASK_SYSTEM = """You are helping Gospel Resonance — a quiet, text-first app that connects life with
the canonical Gospels and the Gospel of Thomas (noncanonical). You must output ONLY valid JSON.

Hard rules:
- NEVER quote or paraphrase scripture in generated fields. Selection is by ID only.
- NEVER speak as Jesus or use first-person divine voice.
- NEVER present generated text as Primary Text.
- Every interpretive field must be humble, non-preachy, non-therapeutic.
- Thomas must always be labeled as noncanonical in your mental model (do not output scripture text).

Narrative context (canonical Gospels only):
- Before thematic commentary on the chosen canonical passages, briefly anchor each in the story: where this moment sits
  in that Gospel (what situation leads in, what happens next)—in plain language, without extended quotation or copying
  verse wording. One or two short sentences per passage is enough.

For each selected text, use one relation label: Resonates with | Deepens | Contrasts with | Grounds
"""

DAILY_SYSTEM = """You are helping Gospel Resonance daily pairing. Output ONLY valid JSON.

Hard rules:
- NEVER quote or paraphrase scripture. Select only by ID from candidates.
- NEVER speak as Jesus.
- Thomas is noncanonical.

Field meanings (do not blur these):
- plain_reading_text: ONLY the chosen CANONICAL passage and today's theme. First briefly place the passage in the Gospel narrative (what is happening around it—before and after in the story), in your own words without quoting verses; then connect to the theme. Write as if the reader has not seen any other text. Do NOT mention Thomas, noncanonical sources, "the other text", "the other passage", "both", "one and the other", "the pair", or compare to anything outside the canonical selection.
- deeper_reading_text: ONLY the chosen THOMAS saying and today's theme. Write as if the reader has not seen the Gospels passage. Do NOT mention Matthew/Mark/Luke/John, canonical gospels, "the other text", "both", "the pair", or compare to anything outside the Thomas saying.
- interpretation_text: ONLY here may you connect the two — dialogue, contrast, or resonance between them.
- why_matched_text: why this pair fits the editorial theme (may reference both selections briefly).
"""


def build_ask_user_message(
    user_text: str,
    canonical_candidates: List[Dict[str, Any]],
    thomas_candidates: List[Dict[str, Any]],
) -> str:
    import json

    canon = json.dumps(canonical_candidates, ensure_ascii=False)
    thom = json.dumps(thomas_candidates, ensure_ascii=False)
    return f"""User input:
{user_text}

Canonical passage candidates (select exactly 2 by id):
{canon}

Thomas saying candidates (select exactly 1 by id):
{thom}

Return JSON with this exact shape:
{{
  "selected_canonical_ids": ["<uuid>","<uuid>"],
  "selected_thomas_id": "<uuid>",
  "relations": [
    {{"id": "<uuid>", "relation_label": "Resonates with"}},
    {{"id": "<uuid>", "relation_label": "Deepens"}},
    {{"id": "<uuid>", "relation_label": "Contrasts with"}}
  ],
  "theme_labels": ["<theme1>", "<theme2>"],
  "interpretation_text": "...",
  "plain_reading_text": "...",
  "deeper_reading_text": "...",
  "why_matched_text": "...",
  "tension_text": null,
  "reflection_questions": ["...","...","..."],
  "confidence_notes": null
}}

Rules:
- relations must cover all 3 selected texts (2 canonical + 1 Thomas, 3 items total).
- Each id in relations must be one of the selected ids.
- reflection_questions: exactly 3 strings.
- plain_reading_text: address the two canonical selections; include brief narrative context (story placement) before
  deeper thematic notes. deeper_reading_text: focus on the Thomas saying (sayings are not a running narrative—context
  may be lighter).
"""


def build_daily_user_message(
    theme_label: str,
    canonical_candidates: List[Dict[str, Any]],
    thomas_candidates: List[Dict[str, Any]],
    recent_refs: str,
) -> str:
    import json

    return f"""Theme of the day (editorial): {theme_label}

Avoid repeating these recent pairings (reference only):
{recent_refs}

Canonical candidates (select 1 by id):
{json.dumps(canonical_candidates, ensure_ascii=False)}

Thomas candidates (select 1 by id):
{json.dumps(thomas_candidates, ensure_ascii=False)}

Return JSON:
{{
  "theme_label": "{theme_label}",
  "selected_canonical_id": "<uuid>",
  "selected_thomas_id": "<uuid>",
  "daily_rationale_text": "one line why this editorial theme fits today",
  "plain_reading_text": "First 1-2 sentences: narrative context in the Gospel (story before/around/after); then theme—canonical only; no Thomas, no 'both'",
  "deeper_reading_text": "2-4 sentences: Thomas saying + theme only; no Gospels, no 'both', no comparison",
  "interpretation_text": "one paragraph: where the two readings meet (comparison allowed here only)",
  "why_matched_text": "1-3 sentences: why this pair for today",
  "tension_text": null or short caveat if helpful,
  "reflection_questions": ["...","...","..."]
}}
"""
