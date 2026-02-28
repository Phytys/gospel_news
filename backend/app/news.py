from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Iterable
from urllib.parse import urlparse

import feedparser
from dateutil import parser as dateparser
import trafilatura


@dataclass
class FeedSource:
    name: str
    url: str


@dataclass
class NewsCandidate:
    title: str
    url: str
    source: str
    published_at: Optional[datetime]
    excerpt: Optional[str]


def load_sources(path: str) -> List[FeedSource]:
    with open(path, "r", encoding="utf-8") as f:
        obj = json.load(f)
    sources = []
    for s in obj.get("sources", []):
        if s.get("url"):
            sources.append(FeedSource(name=s.get("name", "RSS"), url=s["url"]))
    return sources


def _norm_title(t: str) -> str:
    t = t.lower().strip()
    t = re.sub(r"\s+", " ", t)
    t = re.sub(r"[^a-z0-9\s]", "", t)
    return t


def _similar(a: str, b: str) -> float:
    # simple token overlap similarity
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    inter = len(sa.intersection(sb))
    union = len(sa.union(sb))
    return inter / union


def dedupe_candidates(items: Iterable[NewsCandidate], title_sim_threshold: float = 0.78) -> List[NewsCandidate]:
    out: List[NewsCandidate] = []
    seen_urls = set()
    seen_titles: List[str] = []
    for it in items:
        if it.url in seen_urls:
            continue
        nt = _norm_title(it.title)
        is_dup = any(_similar(nt, prev) >= title_sim_threshold for prev in seen_titles)
        if is_dup:
            continue
        seen_urls.add(it.url)
        seen_titles.append(nt)
        out.append(it)
    return out


def fetch_rss_candidates(sources: List[FeedSource], per_source: int = 15) -> List[NewsCandidate]:
    candidates: List[NewsCandidate] = []
    for src in sources:
        feed = feedparser.parse(src.url)
        for entry in feed.entries[:per_source]:
            title = (entry.get("title") or "").strip()
            link = (entry.get("link") or "").strip()
            if not title or not link:
                continue

            published_at: Optional[datetime] = None
            for key in ("published", "updated", "pubDate"):
                if entry.get(key):
                    try:
                        published_at = dateparser.parse(entry.get(key))
                        if published_at and published_at.tzinfo is None:
                            published_at = published_at.replace(tzinfo=timezone.utc)
                    except Exception:
                        published_at = None
                    break

            excerpt = (entry.get("summary") or entry.get("description") or None)
            if isinstance(excerpt, str):
                excerpt = re.sub(r"<[^>]+>", "", excerpt).strip()
                if excerpt == "":
                    excerpt = None

            candidates.append(
                NewsCandidate(
                    title=title,
                    url=link,
                    source=src.name,
                    published_at=published_at,
                    excerpt=excerpt,
                )
            )
    # sort by published_at desc, fallback now
    candidates.sort(key=lambda x: x.published_at or datetime.now(timezone.utc), reverse=True)
    return dedupe_candidates(candidates)


def extract_article_text(url: str, max_chars: int = 8000) -> Optional[str]:
    """Best-effort article extraction. Falls back to None on failure."""
    try:
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return None
        text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
        if not text:
            return None
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) > max_chars:
            text = text[:max_chars].rsplit(" ", 1)[0] + "…"
        return text
    except Exception:
        return None


def infer_outlet(url: str) -> str:
    try:
        host = urlparse(url).netloc
        host = host.replace("www.", "")
        return host or "unknown"
    except Exception:
        return "unknown"
