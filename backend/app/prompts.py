from __future__ import annotations

from typing import Any, Dict, List

JSON_SPEC = {
    "type": "object",
    "required": ["summary", "themes", "gospel_refs", "thomas_ref", "interpretation", "questions"],
    "properties": {
        "summary": {"type": "string"},
        "themes": {"type": "array", "items": {"type": "string"}},
        "gospel_refs": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
        "thomas_ref": {"type": "string"},
        "interpretation": {"type": "string"},
        "questions": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5},
    },
    "additionalProperties": True,
}


def build_digest_messages(
    *,
    title: str,
    outlet: str,
    url: str,
    published_iso: str,
    article_text: str,
    canonical_candidates: List[Dict[str, Any]],
    thomas_candidates: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    """One-shot prompt: summary + select refs + interpretation + questions."""

    system = (
        "You are a careful editor creating a short daily digest. "
        "You MUST output a single JSON object and nothing else. "
        "The user will display scripture text separately, so you must NOT quote scripture. "
        "You are allowed to reference scripture ONLY by selecting refs from the provided candidates. "
        "Any content you generate beyond scripture references is Interpretation (AI-assisted). "
        "Avoid instructions, commands, or prescriptive advice. Use grounded reflective language."
    )

    user = {
        "title": title,
        "outlet": outlet,
        "url": url,
        "published_iso": published_iso,
        "article_text": article_text,
        "task": (
            "1) Write a neutral summary (90-130 words) using only the article_text. "
            "2) Choose 1-2 canonical Gospel references from canonical_candidates and output them verbatim in gospel_refs. "
            "3) Choose exactly 1 Thomas saying from thomas_candidates and output it verbatim in thomas_ref. "
            "4) Write a grounded interpretation (90-150 words) that clearly sounds like interpretation, not scripture. "
            "   Avoid moralizing; connect themes gently (compassion, truth, humility, peacemaking, inner transformation). "
            "5) Provide 3-5 reflective questions (no commands; no 'you should')."
        ),
        "output_json_shape": {
            "summary": "string",
            "themes": ["string", "..."],
            "gospel_refs": ["<ref from canonical_candidates>", "... (max 2)"],
            "thomas_ref": "<ref from thomas_candidates>",
            "interpretation": "string",
            "questions": ["string", "string", "string"]
        },
        "canonical_candidates": canonical_candidates,
        "thomas_candidates": thomas_candidates,
        "hard_rules": [
            "Output JSON ONLY (no markdown).",
            "Do NOT invent refs. gospel_refs and thomas_ref must match candidate refs exactly.",
            "Do NOT quote scripture (no direct quotes).",
            "No instructions or prescriptive advice; only reflections and questions.",
        ],
    }

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": str(user)},
    ]


def build_ask_messages(
    *,
    query: str,
    canonical_matches: List[Dict[str, Any]],
    thomas_matches: List[Dict[str, Any]],
) -> List[Dict[str, str]]:
    system = (
        "You are a careful spiritual-literary guide. "
        "You MUST output a single JSON object and nothing else. "
        "The user will see the primary texts verbatim separately. "
        "Do NOT quote long passages; keep references short. "
        "Any generated content is Interpretation (AI-assisted). "
        "Avoid instructions; ask reflective questions."
    )

    user = {
        "query": query,
        "canonical_matches": canonical_matches,
        "thomas_matches": thomas_matches,
        "task": (
            "Write a short interpretation (90-160 words) that bridges the query and the primary texts, "
            "then provide 3-5 reflective questions."
        ),
        "output_json_shape": {
            "interpretation": "string",
            "questions": ["string", "string", "string"]
        },
        "hard_rules": [
            "Output JSON ONLY (no markdown).",
            "No commands/instructions; only reflections and questions.",
        ],
    }

    return [
        {"role": "system", "content": system},
        {"role": "user", "content": str(user)},
    ]
