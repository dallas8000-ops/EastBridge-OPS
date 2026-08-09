# You downloaded the ZIP — what's inside

This repository is a **monorepo**. The GitHub **Download ZIP** includes everything below.

## Top-level folders (open the zip and look here)

| Folder / file | What it is |
|---------------|------------|
| **`frontend/`** | React UI (TypeScript, Vite) — pages, styles, components |
| **`backend/`** | Django API — regulatory, trade, assistant, playbooks, vendors |
| **`deploy/`** | Railway startup scripts and env examples |
| **`Dockerfile.railway`** | Production build (UI + API in one container) |
| **`railway.toml`** | Railway deploy config |
| **`package.json`** | Run API + UI locally with `npm run dev` |

After unzipping, the folder is named **`EastBridge-OPS-main`**.

Inside **`frontend/src/pages/`** you should see: `OverviewPage.tsx`, `AssistantPage.tsx`, `LoginPage.tsx`, etc.

Inside **`backend/`** you should see: `assistant/`, `regulatory/`, `trade/`, `config/`, etc.

## Not in the ZIP (recreated on your machine)

| Excluded | Why |
|----------|-----|
| `node_modules/` | Run `npm install` in repo root and `frontend/` |
| `frontend/dist/` | Built on deploy; run `npm run build --prefix frontend` locally |
| `.venv/` | Python virtualenv — create locally |
| `.env` | Secrets — copy from `.env.example` |
| `backend/db.sqlite3` | Local database file (gitignored) |
| `backend/media/` | Uploaded files |

## Data **is** in the ZIP (full app image)

Every push updates committed JSON under `backend/fixtures/` — your team sees the **same picture as the running app**:

```
backend/fixtures/
  initial_01_core.json         countries, sources, industries
  initial_02_accounts.json       demo orgs and login
  initial_03_vendors.json        vendor due diligence
  initial_04_regulatory.json     regulatory feed samples
  initial_05_intelligence.json   economic indicators + risk
  initial_06_trade.json          trade procedures
  initial_07_evidence.json       AI assistant source documents
  MANIFEST.json                  checksums (CI verifies on push)
```

After `migrate`, load everything:

```powershell
python backend\manage.py load_initial_data
python backend\manage.py verify_data
```

Open any `initial_*.json` in Notepad or VS Code — no server required.

For **live** regulatory RSS updates on a server, still run [deploy/DATA-SEED.md](deploy/DATA-SEED.md) ingest on Railway. The zip carries the offline snapshot; production can refresh from the network.

## Run from the ZIP (no git clone)

```powershell
cd path\to\EastBridge-OPS-main
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
npm install
cd backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py load_initial_data
..\.venv\Scripts\python manage.py verify_data
cd ..
npm run dev
```

Open http://127.0.0.1:5173

## Wrong zip?

If you see **Chrome cache** files (`Cache`, `Code Cache`, `GPUCache`, etc.), that zip is **not** from this repository. Download only from:

https://github.com/dallas8000-ops/EastBridge-OPS → **Code** → **Download ZIP**

## Verify GitHub has the latest push

Latest commit on `main` should match the top commit shown on GitHub. Pushes go to:

`https://github.com/dallas8000-ops/EastBridge-OPS.git`
