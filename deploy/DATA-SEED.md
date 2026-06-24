# Production data — complete seed sequence

Run **once** after first Railway deploy (or when `/api/v1/countries/` returns `count: 0`).

**Live URL:** https://eastbridge-ops-production.up.railway.app

```bash
railway link -p hearty-enjoyment -e production -s EastBridge-OPS

railway run python manage.py seed_data
railway run python manage.py seed_demo_org
railway run python manage.py ingest --target all
railway run python manage.py sync_trade_procedures --offline
railway run python manage.py embed_evidence --force
railway run python manage.py createsuperuser
railway run python manage.py verify_data
```

Windows (PowerShell): `.\scripts\railway-seed.ps1`

---

## What each command loads

| # | Command | Data created |
|---|---------|----------------|
| 1 | `seed_data` | **6 countries** (UG, KE, TZ, RW, BI, SS); **7 active data sources** (URA, KRA, EAC, World Bank, TRA, RRA, etc.); **5 industries** (solar, agri, fintech, logistics, manufacturing) |
| 2 | `seed_demo_org` | **Demo user** `demo` / `demo12345` (production: use `createsuperuser` instead for clients); **2 orgs** (Helio Solar GmbH, NordWind Energy AG); **4 vendors** with contracts/payments; **alert subscriptions** |
| 3 | `ingest --target all` | **Regulatory changes** from configured sources; **World Bank economic indicators** |
| 4 | `sync_trade_procedures --offline` | **Curated trade procedures** (import/export/customs steps per country) |
| 5 | `embed_evidence --force` | **Vector embeddings** on evidence docs (requires `OPENAI_API_KEY` when `EMBEDDING_PROVIDER=openai`) |
| 6 | `createsuperuser` | **Your production login** (required for client-facing deploy) |
| 7 | `verify_data` | **Pass/fail report** — confirms all minimum counts above |

---

## Verify without Railway CLI

```bash
curl https://eastbridge-ops-production.up.railway.app/api/v1/countries/
# expect count >= 6

curl https://eastbridge-ops-production.up.railway.app/api/v1/health/
# expect {"status":"ok","database":"ok"}
```

Open the app (not the DRF browsable API): https://eastbridge-ops-production.up.railway.app/

---

## Optional: seed on deploy

Railway variable `SEED_ON_DEPLOY=true` runs **only** `seed_data` on container start. It does **not** replace the full sequence above. Set once, redeploy, then set back to `false`.

---

## Not stored in Git

| Item | Where it lives |
|------|----------------|
| Database rows | Railway PostgreSQL |
| Uploaded media | Container disk (ephemeral) or future object storage |
| API keys | Railway Variables / Automation Center vault |
| Built React UI | Built in Docker from `frontend/src` |

Git contains **source code** only. Data is loaded with the commands above.
