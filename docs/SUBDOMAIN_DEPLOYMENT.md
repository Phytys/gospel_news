# Deploying Gospel Resonance as a Subdomain on resonancehub.app

> **Repo layout:** Deploy from the repository root using `docker-compose.yml` (services: `db`, `api`, `worker`, `web`). Code lives under `apps/api`, `apps/web`, `apps/worker`. Set `POSTGRES_DB` / `DATABASE_URL` in `.env` so they agree (see `.env.example`).

**Purpose:** Deploy Gospel Resonance (FastAPI + Postgres + worker + Next.js) as a subdomain on your VPS.

**Difference from static apps:** This is a **full-stack app** (Docker, Postgres, API + Next.js). It does not use the `rsync dist/` pattern alone. Compose runs the stack; **nginx** terminates TLS and splits traffic: **`/` → web (3000)**, **`/api/` → API (8000)**. Details: **[DEPLOYMENT.md](DEPLOYMENT.md)**.

Use **placeholders** below — do not commit real SSH hostnames, keys, or `.env` values.

---

## 1. Server access

| Item | Example |
|------|---------|
| **VPS public IP** | Your DNS A record target (e.g. `203.0.113.10` — replace with your real IP) |
| **SSH** | `ssh -i ~/.ssh/id_ed25519 root@YOUR_VPS_IP` (use your key path) |

---

## 2. Prerequisites on the Server

- **Docker** and **Docker Compose** (`docker compose` or `docker-compose`)
- **nginx** (already present)
- **certbot** (for TLS)

---

## 3. Deployment Steps

### 3.1 Clone the Repo on the Server

```bash
export VPS_IP=YOUR_VPS_IP
export SSH_KEY=~/.ssh/id_ed25519
ssh -i "$SSH_KEY" "root@${VPS_IP}" "sudo mkdir -p /opt/gospellens && sudo chown \$USER:\$USER /opt/gospellens"
# From your machine, rsync (excludes `.env`):
rsync -avz --exclude='.git' --exclude='venv' --exclude='.venv' --exclude='.env' \
  -e "ssh -i $SSH_KEY" \
  ./ "root@${VPS_IP}:/opt/gospellens/"
```

Or clone via git on the server:

```bash
ssh -i ~/.ssh/id_ed25519 "root@${VPS_IP}"
cd /opt
git clone <your-repo-url> gospellens
cd gospellens
```

### 3.2 Create `.env` on the Server

```bash
ssh -i ~/.ssh/id_ed25519 "root@${VPS_IP}"
cd /opt/gospellens
cp .env.example .env
nano .env  # or vim
```

Edit `.env` with:

- `OPENROUTER_API_KEY` — your real key (never commit)
- `POSTGRES_PASSWORD` — strong, unique password
- `ADMIN_TOKEN` — random token for admin endpoints
- `APP_BASE_URL` — your public site URL
- `DATABASE_URL` — must match `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` and use `db:5432` (Docker hostname)
- For same-origin browser → API: `NEXT_PUBLIC_API_URL=` empty or full site URL — see [DEPLOYMENT.md](DEPLOYMENT.md)

### 3.3 Avoid port conflicts

If `8000` or `5432` is already in use on the host, edit **root** `docker-compose.yml` host port mappings (e.g. `8001:8000`, `5433:5432`) and point nginx `proxy_pass` at the **host** ports you chose.

### 3.4 Start the stack

```bash
cd /opt/gospellens
docker compose up -d --build
# or: docker-compose up -d --build
```

### 3.5 Bootstrap corpus, map, and daily

See [README.md](../README.md) bootstrap block. Short form:

```bash
docker compose exec api python -m app.ingest_pipeline
docker compose exec api python -c "import asyncio; from app.services.umap_rebuild import run_rebuild_umap; asyncio.run(run_rebuild_umap())"
# then generate daily (Python one-liner in README)
```

### 3.6 Add Nginx Server Block

**Important:** The UI is **Next.js on port 3000**; the API is **FastAPI on port 8000**. Proxy **`/api/`** to the API and **`/`** to the web app (same pattern as [DEPLOYMENT.md](DEPLOYMENT.md)).

```bash
ssh -i ~/.ssh/id_ed25519 "root@${VPS_IP}"
sudo nano /etc/nginx/sites-available/your-site
```

Example `server` block (replace `YOUR_DOMAIN` and ports if you remapped Compose):

```nginx
server {
    listen 80;
    listen [::]:80;
    server_name YOUR_DOMAIN;

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

If you mapped the API to another host port (e.g. `8010:8000`), use that port in `proxy_pass` for `/api/`.

### 3.7 DNS

Add an **A record** pointing your subdomain to your **VPS public IPv4 address**.

### 3.8 TLS

```bash
sudo certbot --nginx -d YOUR_DOMAIN
```

### 3.9 Reload Nginx

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 4. Quick Reference

| Step | Command / Action |
|------|------------------|
| 1. Deploy code | `rsync` or `git clone` to `/opt/gospellens` |
| 2. Create `.env` | `.env.example` → `.env`, edit secrets + `DATABASE_URL` |
| 3. Start stack | `docker compose up -d --build` |
| 4. Bootstrap | [README.md](../README.md): `ingest_pipeline` → `run_rebuild_umap` → `generate_daily_for_date` |
| 5. Nginx | `/api/` → API port on localhost, `/` → web on localhost |
| 6. DNS | A record → server IP |
| 7. TLS | `sudo certbot --nginx -d YOUR_DOMAIN` |
| 8. Reload | `sudo nginx -t && sudo systemctl reload nginx` |

---

## 5. Port Mapping

| Service | Container port | Typical host (Compose `ports:`) |
|---------|----------------|----------------------------------|
| API | 8000 | 8000 (or another if 8000 is taken) |
| Web | 3000 | 3000 |
| Postgres | 5432 | 5432 (or another if the host already runs Postgres) |

---

## 6. Safety Notes

- **Never** commit `.env` with real keys
- **Never** overwrite other apps’ data on the shared server without checking paths
- **Always** run `nginx -t` before `systemctl reload nginx`

---

## 7. Summary (ops / agent handoff)

**Gospel Resonance subdomain**

- **Server:** your VPS (IP from DNS)
- **SSH:** your user + key; `App path:` `/opt/gospellens` (or your choice)
- **Stack:** Docker Compose — `db`, `api`, `worker`, `web`
- **Nginx:** `https://…/api/*` → API on localhost; `https://…/` → Next.js on localhost
- **Full guide:** [DEPLOYMENT.md](DEPLOYMENT.md) and this file
