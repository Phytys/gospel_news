# Gospel Lens MVP (News + Canonical Gospels + Gospel of Thomas)

This repository is a **minimal, production-deployable MVP**:

- Generates a daily digest (default: **3 stories/day**) from RSS feeds
- Summarizes each story (Interpretation)
- Retrieves relevant passages from:
  - **Canonical Gospels** (Matthew/Mark/Luke/John)
  - **Gospel of Thomas** (114 sayings)
- Produces a short **Interpretation** + **Questions**
- Everything non-scripture is explicitly marked as **Interpretation (AI-assisted)**

The app uses:
- **FastAPI** + Jinja templates
- **Postgres + pgvector**
- **OpenRouter** for chat + embeddings (default chat model: `x-ai/grok-4.1-fast`)

---

## 0) Requirements

- Docker + docker-compose
- An OpenRouter API key
- A VPS (your 4vCPU / 8GB / 160GB is more than enough)

---

## 1) Quick start

1) Copy the env file:

```bash
cp .env.example .env
```

2) Edit `.env`:
- Set `OPENROUTER_API_KEY`
- Set a strong `POSTGRES_PASSWORD`
- Set a random `ADMIN_TOKEN` (used to protect admin endpoints)

3) Start everything:

```bash
docker compose up -d --build
```

4) Initialize DB + load texts + build embeddings:

```bash
docker compose exec api python -m app.scripts.init_db
docker compose exec api python -m app.scripts.ingest_scripture
```

5) Trigger a digest now (instead of waiting for the scheduled time):

```bash
docker compose exec api python -m app.scripts.run_digest
```

6) Open the app:
- http://YOUR_SERVER_IP:8000

---

## 2) What gets downloaded / stored

This MVP downloads public-domain texts on first ingest:

- **World English Bible (WEBP) USFM ZIP** from eBible.org
- **Gospel of Thomas** from gospels.net (Mark M. Mattison translation)

It stores:
- Scripture text chunks (canonical + Thomas)
- Embeddings for those chunks (via OpenRouter embeddings)
- Daily digest outputs and metadata

---

## 3) Admin endpoints

Protected by `ADMIN_TOKEN` header: `X-Admin-Token: ...`

- `POST /api/admin/run-digest`  -> generate today's digest now
- `POST /api/admin/reingest-scripture` -> re-download scripture + re-embed (slow)

---

## 4) Notes

- The app **never lets the model generate scripture text**. It only selects references from retrieved candidates.
- The UI visually separates:
  - **Primary Text** (verbatim) vs
  - **Interpretation (AI-assisted)**

---

## 5) Customization

- RSS sources: edit `backend/config/rss_sources.json`
- Digest time: `DIGEST_TIME_SGT=06:30`
- Models: `OPENROUTER_CHAT_MODEL`, `OPENROUTER_EMBED_MODEL`

---

## 6) License / responsibility

You are responsible for:
- Picking the translations you have the right to use
- Your own legal review
- Moderation and safety policy decisions for your audience
