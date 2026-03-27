# Gospel Resonance — Deployment Guide

## How to deploy (step by step)

### A. On your laptop (local Docker)

1. **Copy env** — `cp .env.example .env` and set at least `OPENROUTER_API_KEY`, `ADMIN_TOKEN`, and Postgres settings.
2. **Align Postgres with `DATABASE_URL`** — The **`db`** container reads `POSTGRES_USER`, `POSTGRES_DB`, and `POSTGRES_PASSWORD`. They must match the user, database name, and password inside `DATABASE_URL` (same values as in `.env.example`’s pattern). If you only set `DATABASE_URL` and omit `POSTGRES_USER` / `POSTGRES_DB`, Compose falls back to defaults and the API will fail to authenticate.
3. **Start the stack** (from the repo root):

   ```bash
   docker compose up -d --build
   ```

   If you only have Compose v1:

   ```bash
   docker-compose up -d --build
   ```

4. **Docker permission denied** (`/var/run/docker.sock`) — Add your user to the `docker` group (`sudo usermod -aG docker "$USER"`, then log out and back in), **or** run once per session: `sg docker -c 'docker-compose up -d --build'`.
5. **After changing DB user/password/database name** — The Postgres data volume was created with the old credentials. Either align `.env` to the existing volume **or** reset the volume (⚠️ **deletes local DB data**):

   ```bash
   docker-compose down -v
   docker-compose up -d
   ```

6. **Smoke test** — `curl http://127.0.0.1:8000/health` → `{"ok":true,...}` and open `http://localhost:3000`.

7. **Bootstrap content** (first time) — See README: `ingest_pipeline`, optional UMAP rebuild for the map, then daily generation if needed.

### B. On a VPS without `git pull` on the server

From a machine that has SSH access and a copy of the repo:

```bash
chmod +x scripts/deploy-vps-rsync.sh
export VPS_HOST=root@YOUR_SERVER_IP
export VPS_PATH=/opt/gospellens
export SSH_IDENTITY=~/.ssh/your_key   # optional
./scripts/deploy-vps-rsync.sh
```

That **rsync**s the tree (excluding `.env` so secrets stay on the VPS) and runs **`docker compose up -d --build`** over SSH. Put a complete `.env` on the server first (`POSTGRES_*` aligned with `DATABASE_URL` as above). Then configure nginx/TLS using the sections below.

### C. Two Compose projects → two Postgres volumes

If you run the same app as **different project names** (e.g. `gospel-resonance` vs `gospellens`), Docker creates **separate** volumes (`gospel-resonance_pgdata` vs `gospellens_pgdata`). **Published dailies** live in `daily_entries` inside whichever volume the running stack uses. A new volume starts **empty**—past archive days appear “gone” until you migrate rows or keep one canonical stack + volume.

### D. `docker-compose` v1 + new Docker Engine (`KeyError: 'ContainerConfig'`)

Prefer the **Compose v2** plugin (`docker compose`, two words). If you must use v1 and hit this when **recreating** (often **`web`** after `npm run build`), force-remove that service’s container and bring it back:

```bash
docker-compose stop web && docker-compose rm -f web
docker-compose up -d
```

Or full reset: `docker-compose down` then `docker-compose up -d --build`.

---

## Verification checklist (local)

1. **`.env`** — `OPENROUTER_API_KEY`, `POSTGRES_PASSWORD`, `DATABASE_URL` matching `POSTGRES_*`, `ADMIN_TOKEN`.
2. **`docker compose up -d --build`** — four services: `db`, `api`, `worker`, `web`.
3. **Bootstrap** (see README): `ingest_pipeline` → `umap_rebuild` → `generate_daily`.
4. **Smoke test** — `GET http://localhost:8000/health`, open `http://localhost:3000`, try Ask.

**Common issues**

- **`NEXT_PUBLIC_API_URL`**: Next.js bakes this at **`docker compose build`** time. If you change it, run `docker compose build web --no-cache` (or full `up --build`).
- **Empty API URL**: Leave `NEXT_PUBLIC_API_URL` unset or empty in `.env` only when the browser will call the API on the **same origin** (nginx routes `/api` to the API container). Otherwise set the full public API base (e.g. `https://api.example.com`).

---

## Production pattern (recommended): one HTTPS host

Browser → **nginx (443)** → static/SSR from **web:3000** for `/`, and **api:8000** for `/api/…`.

### 1. Server

- Docker + Compose
- Repo at e.g. `/opt/gospel-resonance`
- `.env` on the server (never commit)

### 2. `CORS_ORIGINS`

Set to your public site origin, e.g. `https://gospellens.resonancehub.app` (and `http://localhost:3000` only for dev).

### 3. `NEXT_PUBLIC_API_URL` for same-origin

For single-domain deployment:

```env
NEXT_PUBLIC_API_URL=
```

Build the web image **after** setting this (empty). The web app will use relative URLs like `/api/v1/ask`.

If your tooling strips empty variables, use the **full site URL** as the API base instead (only works if the API is exposed at the same host under `/api` — nginx must forward `/api` to the API service):

```env
NEXT_PUBLIC_API_URL=https://gospellens.resonancehub.app
```

### 4. Nginx (illustrative)

```nginx
server {
    listen 443 ssl;
    server_name gospellens.resonancehub.app;

    # TLS certificates (certbot paths) ...

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Publish **ports 3000 and 8000 on localhost only** (Compose default `ports:`); nginx binds 80/443 on the host.

### 5. Port conflicts

If `8000` or `5432` is already used, change **only** the left side of `ports:` in `docker-compose.yml` (e.g. `8001:8000`) and point nginx `proxy_pass` to that host port.

### 6. DNS + TLS

- A record: subdomain → server IP.
- `certbot --nginx -d gospellens.resonancehub.app`

### 7. Automatic daily generation

The **`worker`** service must be **running** (`docker compose ps`). It schedules `generate_daily_for_date` at **`DAILY_GENERATION_TIME_UTC`** (default `06:00` UTC). One-time bootstrap (ingest, UMAP, optional first daily) is still manual; after that, new days are produced on the schedule.

### 8. Deploy / update flow

**Without git on the server:** from your dev machine, run [`scripts/deploy-vps-rsync.sh`](../scripts/deploy-vps-rsync.sh) (rsync + remote `docker compose up -d --build`). See README.

**With git on the server:**

```bash
cd /opt/gospel-resonance
git pull
docker compose up -d --build
```

Admin bootstrap is unchanged from the README (ingest / map / daily) and only runs when needed.

---

## Alternative: API on a separate subdomain

- Web: `https://app.example.com` → port 3000  
- API: `https://api.example.com` → port 8000  

Set `NEXT_PUBLIC_API_URL=https://api.example.com` and `CORS_ORIGINS=https://app.example.com`. Rebuild **web** after changing `NEXT_PUBLIC_API_URL`.
