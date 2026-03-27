# Gospel Resonance MVP

Quiet, text-first resonance between your inner life, the canonical Gospels (WEB), and the Gospel of Thomas (Mattison translation). **Not a news app.**

## Stack

- **apps/api** — FastAPI, Postgres 16 + pgvector, OpenRouter
- **apps/web** — Next.js 14, Tailwind, TanStack Query
- **apps/worker** — APScheduler daily generation
- **scripts** — ingest, UMAP rebuild, daily CLI

## Quick start

```bash
cp .env.example .env
# Set OPENROUTER_API_KEY, ADMIN_TOKEN, POSTGRES_* and DATABASE_URL (user/db/password must match — see docs/DEPLOYMENT.md)

docker compose up -d --build
```

If your machine only has Compose v1, use a hyphen: `docker-compose up -d --build`. If Docker says **permission denied** on the socket, add your user to the `docker` group or run via `sg docker -c 'docker-compose up -d --build'`.

**Full deploy steps (local + VPS, Postgres alignment, troubleshooting):** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

Bootstrap data (inside API container):

```bash
# 1) Required once: texts + embeddings (Ask, Daily, Map all need this).
docker compose exec api python -m app.ingest_pipeline

# 2) Optional: Map tab only — UMAP projection (not required for Daily).
docker compose exec api python -c "import asyncio; from app.services.umap_rebuild import run_rebuild_umap; asyncio.run(run_rebuild_umap())"

# 3) Optional: only if you want today’s daily immediately — worker/API usually create it automatically after deploy.
docker compose exec api python -c "
import asyncio
from datetime import date
from app.db import AsyncSessionLocal, init_db_schema
from app.services.daily_service import generate_daily_for_date
async def main():
    await init_db_schema()
    async with AsyncSessionLocal() as s:
        await generate_daily_for_date(s, date.today())
asyncio.run(main())
"
```

- **API:** http://localhost:8000 — OpenAPI at `/docs`
- **Web:** http://localhost:3000

### Deploy to VPS (no `git pull` on the server)

Use [scripts/deploy-vps-rsync.sh](scripts/deploy-vps-rsync.sh): rsync from your laptop to the VPS (`.env` is **not** copied—keep secrets only on the server), then SSH runs `docker compose up -d --build`.

```bash
chmod +x scripts/deploy-vps-rsync.sh
export VPS_HOST=root@YOUR_SERVER_IP
export VPS_PATH=/opt/gospellens
export SSH_IDENTITY=~/.ssh/your_key   # optional
./scripts/deploy-vps-rsync.sh
```

On the VPS, create `.env` once from `.env.example` if you have not already. Nginx/TLS: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/SUBDOMAIN_DEPLOYMENT.md](docs/SUBDOMAIN_DEPLOYMENT.md).

### Automatic daily generation

The **`worker`** container runs a scheduler (APScheduler) that calls the same logic as `POST /api/v1/admin/generate-daily` once per **calendar day** in UTC.

- **`DAILY_GENERATION_TIME_UTC`** — when to run, e.g. `06:00` (default). Format `HH:MM` 24h.
- **`RUN_DAILY_ON_STARTUP`** — worker runs one daily generation when it starts (default **`true`**) so deploys are not stuck until the next cron.
- **`ENSURE_DAILY_ON_API_STARTUP`** — API process also ensures today’s daily exists shortly after startup (default **`true`**). Set `false` if you only want the worker to generate. Corpus must still be ingested once (`ingest_pipeline`).

Ensure `docker compose` includes **`worker`** (`docker compose ps` should show it **Up**). After changing these variables, restart the worker: `docker compose up -d worker`.

Admin (header `X-Admin-Token`):

- `POST /api/v1/admin/ingest-texts`
- `POST /api/v1/admin/rebuild-map`
- `POST /api/v1/admin/generate-daily`

## Docs

| Doc | Purpose |
|-----|---------|
| [docs/PRODUCT_SPEC.md](docs/PRODUCT_SPEC.md) | Product thesis & MVP scope |
| [docs/API_SPEC.md](docs/API_SPEC.md) | HTTP API summary |
| [docs/DATA_MODEL.md](docs/DATA_MODEL.md) | Postgres tables |
| [docs/PROMPT_RULES.md](docs/PROMPT_RULES.md) | LLM guardrails |
| [docs/PRIVACY.md](docs/PRIVACY.md) | Prompt storage & privacy |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | **Deploy runbook** (local + VPS rsync), nginx, TLS, `NEXT_PUBLIC_API_URL` |
| [docs/SUBDOMAIN_DEPLOYMENT.md](docs/SUBDOMAIN_DEPLOYMENT.md) | VPS subdomain (e.g. resonancehub) — server path, nginx |

## Security (GitHub)

- **Never commit `.env`** — it is gitignored; use `.env.example` only with placeholders.
- If you ever committed real keys or tokens, **rotate them** in OpenRouter and on the server (Git history may still contain them).
- Deployment docs use **placeholders** for hosts and SSH keys — keep real IPs and key names out of the repo.

## License / responsibility

You are responsible for translation rights, legal review, and audience safety choices.
