#!/usr/bin/env bash
# Deploy Gospel Resonance to a VPS by rsync + remote Docker Compose (no git on server).
#
# Usage (from repo root):
#   export VPS_HOST=root@YOUR_SERVER_IP
#   export VPS_PATH=/opt/gospellens
#   export SSH_IDENTITY=~/.ssh/your_key   # optional, defaults to ~/.ssh/id_rsa
#   ./scripts/deploy-vps-rsync.sh
#
# Prereq: .env already exists on the server (rsync excludes .env). POSTGRES_USER / POSTGRES_DB /
# POSTGRES_PASSWORD must match DATABASE_URL — see docs/DEPLOYMENT.md "How to deploy".
# After first deploy, run ingest once on the server if needed (see README).

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

VPS_HOST="${VPS_HOST:?Set VPS_HOST, e.g. root@203.0.113.10}"
VPS_PATH="${VPS_PATH:?Set VPS_PATH, e.g. /opt/gospellens}"
SSH_IDENTITY="${SSH_IDENTITY:-$HOME/.ssh/id_rsa}"
# Options only — do not prefix with `ssh` here (see remote `ssh` below).
SSH_OPTS=(-o StrictHostKeyChecking=accept-new -i "$SSH_IDENTITY")
RSYNC_REMOTE="ssh ${SSH_OPTS[*]}"

echo "==> rsync $(pwd) -> ${VPS_HOST}:${VPS_PATH}/"
rsync -avz \
  --exclude='.git/' \
  --exclude='.env' \
  --exclude='node_modules/' \
  --exclude='.venv/' \
  --exclude='venv/' \
  --exclude='**/.next/' \
  --exclude='.cursor/' \
  -e "$RSYNC_REMOTE" \
  ./ "${VPS_HOST}:${VPS_PATH}/"

echo "==> remote: docker compose up -d --build"
# Prefer Compose v2 plugin; fall back to docker-compose v1.
ssh "${SSH_OPTS[@]}" "$VPS_HOST" "cd $(printf '%q' "$VPS_PATH") && \
  if docker compose version >/dev/null 2>&1; then \
    docker compose up -d --build; \
  else \
    docker-compose up -d --build; \
  fi"

echo "==> done. Check: ssh ... 'cd $VPS_PATH && docker compose ps'"
