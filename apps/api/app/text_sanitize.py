"""Normalize display text from USFM / legacy sources."""

from __future__ import annotations

import re


def strip_stray_usfm_asterisks(s: str) -> str:
    """Remove leftover * tokens from USFM markup (e.g. 'He * said *' from \\wj handling)."""
    if not s:
        return s
    s = re.sub(r"\s*\*\s*", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def fix_broken_contractions(s: str) -> str:
    """Fix spaces inside contractions sometimes left by extraction (e.g. Couldn' t → Couldn't)."""
    if not s:
        return s
    s = re.sub(r"(\w+)['\u2019]\s+([ts])\b", r"\1'\2", s, flags=re.IGNORECASE)
    return s


def normalize_punctuation_spacing(s: str) -> str:
    """Tidy spaces left when * tokens were removed (e.g. 'said ,' → 'said,')."""
    if not s:
        return s
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r"\s+\.", ".", s)
    s = re.sub(r"\s+!", "!", s)
    s = re.sub(r"\s+\?", "?", s)
    s = re.sub(r"\s+:", ":", s)
    s = re.sub(r"\s+;", ";", s)
    # comma/period often want one space after
    s = re.sub(r",([^\s\d])", r", \1", s)
    return s


def sanitize_source_display(s: str) -> str:
    """Apply all source-text display normalizations."""
    s = strip_stray_usfm_asterisks(s)
    s = fix_broken_contractions(s)
    s = normalize_punctuation_spacing(s)
    s = re.sub(r"\s+", " ", s).strip()
    return s
