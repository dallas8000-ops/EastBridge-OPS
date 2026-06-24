# Deploy EastBridge on Railway (Gilliom)

**Portfolio:** [gilliomfrontlinedigital.com](https://gilliomfrontlinedigital.com/)  
**Automation hub:** [Deployment-Stripe-center](https://github.com/dallas8000-ops/Deployment-Stripe-center) → [stripe-installer.gilliomfrontlinedigital.com](https://stripe-installer.gilliomfrontlinedigital.com/login)  
**EastBridge target URL:** `https://eastbridge.gilliomfrontlinedigital.com`  
**Railway fallback:** `https://eastbridge-production.up.railway.app`

Railway runs **one web service** from `Dockerfile.railway`: nginx on `$PORT` serves React and proxies `/api/` to gunicorn. No Docker Compose on Railway.

For VPS / full Docker Compose (worker, beat, Redis), see [DEPLOY.md](DEPLOY.md).

---

## Recommended: deploy via Automation Center

Use your existing [Deployment-Stripe-center](https://github.com/dallas8000-ops/Deployment-Stripe-center) workflow instead of manual Railway clicks.

| Step | Action |
|------|--------|
| 1 | Open [stripe-installer.gilliomfrontlinedigital.com](https://stripe-installer.gilliomfrontlinedigital.com/login) |
| 2 | **Projects** → create project — Git URL `https://github.com/dallas8000-ops/EastBridge-OPS` |
| 3 | **Vault** → store `RAILWAY_API_TOKEN`, `OPENAI_API_KEY` (and `SECRET_KEY` if you prefer vault over Railway UI) |
| 4 | Confirm **deploy.config.json** in repo root (platform `railway`, production URL) |
| 5 | **Transfer** tab or `/deploy` → run deploy to Railway (creates/links Postgres, pushes env) |
| 6 | Railway → **Networking** → custom domain `eastbridge.gilliomfrontlinedigital.com` |
| 7 | Porkbun DNS → CNAME `eastbridge` → Railway CNAME target |
| 8 | Set `CUSTOM_DOMAIN=eastbridge.gilliomfrontlinedigital.com` on the web service |
| 9 | `railway run` ingest + embed (see below) |

This repo includes `deploy.config.json` and `railway.toml` so the scanner and transfer module detect Railway + health path `/api/v1/health/`.

---

## Manual Railway setup

### 1. Create project

1. Railway → **New Project** → **Deploy from GitHub** → `EastBridge-OPS`.
2. Builds via `railway.toml` + `Dockerfile.railway`.
3. Add **PostgreSQL** → link `DATABASE_URL` to the web service.

### 2. Required variables

| Variable | Value |
|----------|--------|
| `DEBUG` | `False` |
| `SECRET_KEY` | 50+ char random string |
| `CUSTOM_DOMAIN` | `eastbridge.gilliomfrontlinedigital.com` |
| `OPENAI_API_KEY` | `sk-...` |
| `EMBEDDING_PROVIDER` | `openai` |
| `ANSWER_PROVIDER` | `openai` |

See [deploy/gilliom-railway.env.example](deploy/gilliom-railway.env.example).

`ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` auto-include `RAILWAY_PUBLIC_DOMAIN` and `CUSTOM_DOMAIN`.

### 3. DNS (Porkbun / Google Domains)

| Type | Host | Target |
|------|------|--------|
| CNAME | `eastbridge` | Railway networking CNAME (e.g. `xxxx.up.railway.app`) |

Do **not** point the portfolio root `gilliomfrontlinedigital.com` at EastBridge — that host stays the marketing site ([DevCollective](https://gilliomfrontlinedigital.com/)).

Railway provisions HTTPS when DNS resolves.

### 4. Google Search Console

After deploy:

1. Add property `https://eastbridge.gilliomfrontlinedigital.com`
2. **URL inspection** → request indexing on `/`
3. `frontend/public/robots.txt` allows crawlers

### 5. Initialize data (first run)

```bash
railway login
railway link

railway run python manage.py seed_data
railway run python manage.py ingest --target all
railway run python manage.py sync_trade_procedures --offline
railway run python manage.py embed_evidence --force
railway run python manage.py createsuperuser
```

Use `createsuperuser` for client accounts — demo credentials are dev-only.

### 6. Health check

```bash
curl https://eastbridge.gilliomfrontlinedigital.com/api/v1/health/
```

Expected: `{"status":"ok","database":"ok"}`

---

## Gilliom URL map

| Surface | URL |
|---------|-----|
| Portfolio marketing | https://gilliomfrontlinedigital.com |
| Automation / deploy hub | https://stripe-installer.gilliomfrontlinedigital.com |
| EastBridge (production) | https://eastbridge.gilliomfrontlinedigital.com |
| EastBridge (Railway) | https://eastbridge-production.up.railway.app |

---

## Railway limitations

| Feature | On Railway | Workaround |
|---------|------------|------------|
| Docker Compose | Not supported | `Dockerfile.railway` single container |
| Celery worker + beat | Not default | Second Railway service + Redis plugin |
| Scheduled ingestion | Needs beat | `railway run python manage.py ingest --target all` |
| pgvector | May be missing | JSON embedding search fallback |
| Media uploads | Ephemeral disk | Object storage if needed |
| fastembed | Large boot download | `EMBEDDING_PROVIDER=openai` |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `DisallowedHost` | Set `CUSTOM_DOMAIN=eastbridge.gilliomfrontlinedigital.com` |
| CSRF / login fails | Redeploy after `CUSTOM_DOMAIN` set |
| DB connection error | Link `DATABASE_URL`; SSL auto on Railway |
| No assistant evidence | Run ingest + `embed_evidence` |
| Automation Center deploy fails | Vault `RAILWAY_API_TOKEN`; check deploy logs |

## Local development

```powershell
npm run dev
```

Single terminal, no popups.
