# Deploy EastBridge on your domain

Production runs as **one site**: nginx serves the React app and proxies `/api/` and `/media/` to Django (gunicorn). No Vite dev server, no PowerShell popups, no separate ports for clients.

**Deploying on Railway?** Use **[DEPLOY-RAILWAY.md](DEPLOY-RAILWAY.md)** — single container, `$PORT`, Postgres plugin, custom domain + Google DNS.

## Requirements

- Docker and Docker Compose
- A server (VPS, Railway, Render, etc.)
- Domain DNS pointing to the server (e.g. `ops.yourcompany.com`)
- OpenAI API key (recommended for reliable assistant answers)

## 1. Configure environment

Copy and edit `.env` on the server:

```bash
cp .env.example .env
```

Production values:

```env
DEBUG=False
SECRET_KEY=<long-random-string-at-least-50-chars>
ALLOWED_HOSTS=ops.yourcompany.com,yourcompany.com
CSRF_TRUSTED_ORIGINS=https://ops.yourcompany.com
CORS_ALLOWED_ORIGINS=https://ops.yourcompany.com

DATABASE_URL=postgres://eastbridge:eastbridge@db:5432/eastbridge
REDIS_URL=redis://redis:6379/0

EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
ANSWER_PROVIDER=openai
OPENAI_CHAT_MODEL=gpt-4o-mini
```

`CORS_ALLOWED_ORIGINS` is only needed if the UI and API are on different origins. With the included nginx setup they share one domain.

## 2. Start production stack

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up --build -d
```

Or from the repo root on Windows:

```powershell
npm run prod:up
```

- **Public URL:** `http://your-server-ip` (port 80) or your domain after DNS + TLS
- **Dev Docker UI:** port `8080` if using the base compose file without prod overlay

## 3. Initialize data (first run only)

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py seed_data
docker compose exec backend python manage.py ingest --target all
docker compose exec backend python manage.py sync_trade_procedures --offline
docker compose exec backend python manage.py embed_evidence --force
```

Create client accounts (replace demo users for production):

```bash
docker compose exec backend python manage.py createsuperuser
```

## 4. HTTPS (recommended)

Put **Caddy**, **nginx**, or your cloud load balancer in front of the container on port 80. Terminate TLS there and forward to the frontend container.

Set `CSRF_TRUSTED_ORIGINS` and `ALLOWED_HOSTS` to your `https://` domain.

## 5. Health check

```bash
curl https://ops.yourcompany.com/api/v1/health/
```

Expected: `{"status":"ok","database":"ok"}`

## Local development (no popups)

```powershell
npm run dev
```

Runs API and UI in **one terminal**. Press `Ctrl+C` to stop. No extra PowerShell windows.

## Reliability checklist

| Item | Action |
|------|--------|
| Assistant answers | Set `OPENAI_API_KEY` + `ANSWER_PROVIDER=openai` |
| Evidence search | Run `embed_evidence` after ingest |
| Regulatory data | Celery beat ingests every 6h (worker + beat containers) |
| Smoke test | `npm run smoke` or `.\scripts\smoke-test.ps1` |
