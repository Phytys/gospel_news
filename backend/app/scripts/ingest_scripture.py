from __future__ import annotations

import asyncio
import io
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen

from bs4 import BeautifulSoup
from sqlalchemy import delete, select

from ..db import AsyncSessionLocal, init_db_schema
from ..models import ScriptureChunk
from ..settings import settings
from ..embeddings import embed_texts


WEBP_USFM_ZIP_URL = "https://ebible.org/engwebp/engwebp_usfm.zip"
THOMAS_URL = "https://www.gospels.net/thomas"

BOOK_MAP = {
    "MAT": "Matthew",
    "MRK": "Mark",
    "LUK": "Luke",
    "JHN": "John",
}


@dataclass
class Verse:
    chapter: int
    verse_raw: str  # e.g. "1" or "1-2"
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

    # Remove footnotes and crossrefs
    s = re.sub(r"\\f\s+.*?\\f\*", " ", s, flags=re.DOTALL)
    s = re.sub(r"\\x\s+.*?\\x\*", " ", s, flags=re.DOTALL)

    # Remove common paired markers but keep content
    paired = [
        "add", "wj", "bd", "it", "em", "sc", "sig", "nd", "pn", "qt", "tl", "k", "qs"
    ]
    for tag in paired:
        s = s.replace(f"\\{tag} ", " ").replace(f"\\{tag}*", " ")

    # Remove remaining backslash markers (best-effort)
    s = re.sub(r"\\[a-zA-Z0-9+]+\s*", " ", s)

    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
    return s


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
            # May contain multiple verses in a single line
            parts = verse_re.split(line)
            # parts: [pre, "\v 1", text1, "\v 2", text2, ...]
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

        # Other lines: append to current verse buffer if we're inside a verse
        if current_verse is not None:
            buf.append(line)

    flush()
    return verses


def chunk_passages(book: str, verses: List[Verse], chunk_size: int = 5) -> List[Tuple[str, str, Dict]]:
    """Return list of (ref, text, meta) for passage chunks."""
    by_ch: Dict[int, List[Verse]] = {}
    for v in verses:
        by_ch.setdefault(v.chapter, []).append(v)

    chunks: List[Tuple[str, str, Dict]] = []
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
            meta = {"chapter": ch, "start_verse": start, "end_verse": end, "chunk_size": chunk_size}
            chunks.append((ref, text, meta))
    return chunks


def download_bytes(url: str) -> bytes:
    with urlopen(url) as resp:
        return resp.read()


def load_webp_gospels() -> List[Tuple[str, str, str, Dict, str]]:
    """Return list of (source, doc, ref, text, meta, chunk_kind)."""
    data = download_bytes(WEBP_USFM_ZIP_URL)
    zf = zipfile.ZipFile(io.BytesIO(data))

    # Find relevant USFM files for the four gospels.
    # Filenames vary; match by containing '\\id MAT' etc OR by filename containing book code.
    name_list = zf.namelist()

    # Prefer files whose names contain e.g. 'MAT' and end with .usfm
    candidates = {}
    for code in BOOK_MAP:
        matches = [n for n in name_list if n.lower().endswith(".usfm") and code.lower() in n.lower()]
        if matches:
            candidates[code] = matches[0]

    # Fallback: scan contents for \id markers if needed
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

    all_rows: List[Tuple[str, str, str, Dict]] = []
    for code, fname in candidates.items():
        book = BOOK_MAP[code]
        usfm = zf.read(fname).decode("utf-8", errors="ignore")
        verses = parse_usfm_book(usfm, code)

        # Verse chunks
        for v in verses:
            ref = f"{book} {v.chapter}:{v.verse_raw}"
            meta = {"chapter": v.chapter, "verse": v.verse_raw, "book_code": code}
            all_rows.append((book, ref, v.text, meta, "verse"))

        # Passage chunks
        for ref, txt, meta in chunk_passages(book, verses, chunk_size=5):
            meta["book_code"] = code
            all_rows.append((book, ref, txt, meta, "passage"))

    return all_rows


def load_thomas_sayings() -> List[Tuple[str, str, str, Dict, str]]:
    html = download_bytes(THOMAS_URL).decode("utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")
    text = re.sub(r"\r", "", text)

    # Capture each Saying block
    pattern = re.compile(r"^Saying\s+(\d+):\s*(.+?)\n\s*\n(.+?)(?=\nSaying\s+\d+:|\Z)", re.MULTILINE | re.DOTALL)
    rows: List[Tuple[str, str, str, Dict, str]] = []

    for m in pattern.finditer(text):
        num = int(m.group(1))
        title = m.group(2).strip()
        body = m.group(3).strip()
        body = re.sub(r"\s+", " ", body).strip()
        ref = f"Thomas {num}"
        meta = {"saying": num, "title": title, "source_url": THOMAS_URL}
        rows.append(("Thomas", ref, body, meta, "saying"))

    return rows


async def main() -> None:
    await init_db_schema()

    canonical_rows = load_webp_gospels()
    thomas_rows = load_thomas_sayings()

    embed_model = settings.openrouter_embed_model
    embed_dims = settings.openrouter_embed_dimensions

    async with AsyncSessionLocal() as session:
        # Delete existing chunks for this embedding configuration to keep it simple/repeatable
        await session.execute(
            delete(ScriptureChunk).where(
                ScriptureChunk.embedding_model == embed_model,
                ScriptureChunk.embedding_dimensions == embed_dims,
            )
        )
        await session.commit()

        to_insert: List[ScriptureChunk] = []

        # Canonical
        for doc, ref, text, meta, kind in canonical_rows:
            to_insert.append(
                ScriptureChunk(
                    source="canonical",
                    doc=doc,
                    ref=ref,
                    chunk_kind=kind,
                    text=text,
                    meta=meta,
                    embedding_model=embed_model,
                    embedding_dimensions=embed_dims,
                )
            )

        # Thomas
        for doc, ref, text, meta, kind in thomas_rows:
            to_insert.append(
                ScriptureChunk(
                    source="thomas",
                    doc=doc,
                    ref=ref,
                    chunk_kind=kind,
                    text=text,
                    meta=meta,
                    embedding_model=embed_model,
                    embedding_dimensions=embed_dims,
                )
            )

        session.add_all(to_insert)
        await session.commit()

        # Now embed in batches
        res = await session.execute(
            select(ScriptureChunk).where(
                ScriptureChunk.embedding_model == embed_model,
                ScriptureChunk.embedding_dimensions == embed_dims,
                ScriptureChunk.embedding.is_(None),
            )
        )
        rows = list(res.scalars().all())
        print(f"Embedding {len(rows)} scripture chunks with {embed_model} dims={embed_dims}...")

        batch_size = 64
        for i in range(0, len(rows), batch_size):
            batch = rows[i : i + batch_size]
            texts = [r.text for r in batch]
            vectors = await embed_texts(texts)
            for r, v in zip(batch, vectors):
                r.embedding = v
            await session.commit()
            print(f"Embedded {min(i + batch_size, len(rows))}/{len(rows)}")

        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
