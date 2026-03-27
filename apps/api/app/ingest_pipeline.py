"""Ingest WEB gospels + Thomas into source_texts; embeddings in text_embeddings."""

from __future__ import annotations

import asyncio
import io
import re
import uuid
import zipfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen

from bs4 import BeautifulSoup
from sqlalchemy import delete, select

from .db import AsyncSessionLocal, init_db_schema
from .embeddings import embed_texts
from .models import SourceText, TextEmbedding
from .settings import settings
from .text_sanitize import strip_stray_usfm_asterisks

WEB_USFM_ZIP_URL = "https://eBible.org/Scriptures/eng-web_usfm.zip"
THOMAS_URL = "https://www.gospels.net/thomas"
BOOK_MAP = {"MAT": "Matthew", "MRK": "Mark", "LUK": "Luke", "JHN": "John"}
SOURCE_WEB = "World English Bible"
SOURCE_THOMAS = "Mark M. Mattison (Gospel of Thomas, noncanonical source text)"


@dataclass
class Verse:
    chapter: int
    verse_raw: str
    text: str

    @property
    def verse_start(self) -> int:
        m = re.match(r"(\d+)", self.verse_raw)
        return int(m.group(1)) if m else 0

    @property
    def verse_end(self) -> int:
        m = re.match(r"(\d+)(?:-(\d+))?$", self.verse_raw)
        if not m:
            return self.verse_start
        return int(m.group(2)) if m.group(2) else int(m.group(1))


def _clean_usfm(s: str) -> str:
    s = s.replace("\n", " ")
    s = re.sub(r"\\f\s+.*?\\f\*", " ", s, flags=re.DOTALL)
    s = re.sub(r"\\x\s+.*?\\x\*", " ", s, flags=re.DOTALL)
    s = re.sub(r'\|\s*strong\s*=\s*["\'][^"\']*["\']', "", s)
    paired = ["add", "wj", "bd", "it", "em", "sc", "sig", "nd", "pn", "qt", "tl", "k", "qs"]
    for tag in paired:
        s = s.replace(f"\\{tag} ", " ").replace(f"\\{tag}*", " ")
    s = re.sub(r"\\[a-zA-Z0-9+]+\s*", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return strip_stray_usfm_asterisks(s)


def parse_usfm_book(usfm_text: str, book_code: str) -> List[Verse]:
    lines = usfm_text.splitlines()
    chapter: Optional[int] = None
    current_verse: Optional[str] = None
    buf: List[str] = []
    verses: List[Verse] = []

    def flush():
        nonlocal buf, current_verse, chapter
        if chapter is None or current_verse is None:
            buf = []
            return
        text = _clean_usfm(" ".join(buf))
        if text:
            verses.append(Verse(chapter=chapter, verse_raw=current_verse, text=text))
        buf = []

    verse_re = re.compile(r"(\\v\s+\d+(?:-\d+)?)")
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("\\c "):
            flush()
            try:
                chapter = int(line.split()[1])
            except Exception:
                chapter = None
            current_verse = None
            buf = []
            continue
        if "\\v " in line:
            parts = verse_re.split(line)
            i = 0
            while i < len(parts):
                seg = parts[i]
                if seg.startswith("\\v"):
                    flush()
                    toks = seg.split()
                    current_verse = toks[1] if len(toks) > 1 else None
                    buf = []
                    if i + 1 < len(parts):
                        buf.append(parts[i + 1])
                    i += 2
                else:
                    if current_verse is not None:
                        buf.append(seg)
                    i += 1
            continue
        if current_verse is not None:
            buf.append(line)
    flush()
    return verses


def chunk_passages(book: str, verses: List[Verse], chunk_size: int = 5) -> List[Tuple[str, str, Dict[str, Any]]]:
    by_ch: Dict[int, List[Verse]] = {}
    for v in verses:
        by_ch.setdefault(v.chapter, []).append(v)
    chunks: List[Tuple[str, str, Dict[str, Any]]] = []
    for ch in sorted(by_ch.keys()):
        vs = sorted(by_ch[ch], key=lambda x: x.verse_start)
        for i in range(0, len(vs), chunk_size):
            group = vs[i : i + chunk_size]
            if not group:
                continue
            start = group[0].verse_start
            end = group[-1].verse_end
            ref = f"{book} {ch}:{start}-{end}" if start != end else f"{book} {ch}:{start}"
            text = " ".join(v.text for v in group).strip()
            meta = {
                "chapter_start": ch,
                "verse_start": start,
                "chapter_end": ch,
                "verse_end": end,
            }
            chunks.append((ref, text, meta))
    return chunks


def download_bytes(url: str) -> bytes:
    with urlopen(url) as resp:
        return resp.read()


def load_web_gospels() -> List[Tuple[str, str, str, Dict[str, Any], str]]:
    data = download_bytes(WEB_USFM_ZIP_URL)
    zf = zipfile.ZipFile(io.BytesIO(data))
    name_list = zf.namelist()
    candidates: Dict[str, str] = {}
    for code in BOOK_MAP:
        matches = [n for n in name_list if n.lower().endswith(".usfm") and code.lower() in n.lower()]
        if matches:
            candidates[code] = matches[0]
    for code in BOOK_MAP:
        if code in candidates:
            continue
        for n in name_list:
            if not n.lower().endswith(".usfm"):
                continue
            txt = zf.read(n).decode("utf-8", errors="ignore")
            if f"\\id {code}" in txt:
                candidates[code] = n
                break

    all_rows: List[Tuple[str, str, str, Dict[str, Any], str]] = []
    for code, fname in candidates.items():
        book = BOOK_MAP[code]
        usfm = zf.read(fname).decode("utf-8", errors="ignore")
        verses = parse_usfm_book(usfm, code)
        for v in verses:
            ref = f"{book} {v.chapter}:{v.verse_raw}"
            meta = {
                "chapter_start": v.chapter,
                "verse_start": v.verse_start,
                "chapter_end": v.chapter,
                "verse_end": v.verse_end,
                "book_code": code,
            }
            all_rows.append((book, ref, v.text, meta, "verse"))
        for ref, txt, meta in chunk_passages(book, verses, chunk_size=5):
            meta = {**meta, "book_code": code}
            all_rows.append((book, ref, txt, meta, "passage"))
    return all_rows


def load_thomas_sayings() -> List[Tuple[str, str, str, Dict[str, Any], str]]:
    html = download_bytes(THOMAS_URL).decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    text = re.sub(r"\r", "", text)
    pattern = re.compile(r"^Saying\s+(\d+):\s*(.+?)\n\s*\n(.+?)(?=\nSaying\s+\d+:|\Z)", re.MULTILINE | re.DOTALL)
    rows: List[Tuple[str, str, str, Dict[str, Any], str]] = []
    for m in pattern.finditer(text):
        num = int(m.group(1))
        title = m.group(2).strip()
        body = m.group(3).strip()
        body = re.sub(r"\s+", " ", body).strip()
        ref = f"Thomas {num}"
        meta = {"saying_number": num, "title": title, "source_url": THOMAS_URL}
        rows.append(("Thomas", ref, body, meta, "saying"))
    return rows


def _sort_key(tradition: str, book: str, ref_label: str) -> str:
    return f"{tradition}/{book}/{ref_label}"


async def run_ingest(*, clear_existing: bool = True) -> int:
    await init_db_schema()
    canonical_rows = load_web_gospels()
    thomas_rows = load_thomas_sayings()

    async with AsyncSessionLocal() as session:
        if clear_existing:
            await session.execute(delete(SourceText))
            await session.commit()

        to_add: List[SourceText] = []
        for book, ref_label, text, meta, chunk_type in canonical_rows:
            st = SourceText(
                id=uuid.uuid4(),
                tradition="canonical",
                chunk_type=chunk_type,
                book=book,
                chapter_start=meta.get("chapter_start"),
                verse_start=meta.get("verse_start"),
                chapter_end=meta.get("chapter_end"),
                verse_end=meta.get("verse_end"),
                saying_number=None,
                ref_label=ref_label,
                title=None,
                text=text,
                theme_tags=[],
                source_translation=SOURCE_WEB,
                sort_key=_sort_key("canonical", book, ref_label),
            )
            to_add.append(st)
        for book, ref_label, text, meta, chunk_type in thomas_rows:
            st = SourceText(
                id=uuid.uuid4(),
                tradition="thomas",
                chunk_type="saying",
                book="Thomas",
                saying_number=meta.get("saying_number"),
                ref_label=ref_label,
                title=meta.get("title"),
                text=text,
                theme_tags=[],
                source_translation=SOURCE_THOMAS,
                sort_key=_sort_key("thomas", "Thomas", ref_label),
            )
            to_add.append(st)

        session.add_all(to_add)
        await session.commit()

        res = await session.execute(select(SourceText))
        rows = list(res.scalars().all())
        print(f"Inserted {len(rows)} source texts. Embedding…")

        batch_size = 64
        embed_model = settings.openrouter_embed_model
        embed_dims = settings.openrouter_embed_dimensions
        ev = settings.embedding_version

        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [r.text for r in batch]
            vectors = await embed_texts(texts)
            for r, v in zip(batch, vectors):
                session.add(
                    TextEmbedding(
                        source_text_id=r.id,
                        embedding_model=embed_model,
                        embedding_dim=embed_dims,
                        embedding_version=ev,
                        embedding=v,
                    )
                )
            await session.commit()
            print(f"Embedded {min(i + batch_size, len(rows))}/{len(rows)}")

    return len(rows)


async def main() -> None:
    n = await run_ingest()
    print(f"Done. {n} texts with embeddings.")


if __name__ == "__main__":
    asyncio.run(main())
