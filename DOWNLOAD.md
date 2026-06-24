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

## Not in the ZIP (normal — recreated on your machine or on Railway)

| Excluded | Why |
|----------|-----|
| `node_modules/` | Run `npm install` in repo root and `frontend/` |
| `frontend/dist/` | Built on deploy; run `npm run build --prefix frontend` locally |
| `.venv/` | Python virtualenv — create locally |
| `.env` | Secrets — copy from `.env.example` |
| `backend/db.sqlite3` | Local database file |
| `backend/media/` | Uploaded files |

Live **database content** (regulatory data, embeddings) is created on the server with `seed_data` and `ingest` — not stored in Git. See **[deploy/DATA-SEED.md](deploy/DATA-SEED.md)** for the complete command list.

## Run from the ZIP (no git clone)

```powershell
cd path\to\EastBridge-OPS-main
copy .env.example .env
python -m venv .venv
.\.venv\Scripts\pip install -r backend\requirements.txt
npm install
cd backend
..\.venv\Scripts\python manage.py migrate
..\.venv\Scripts\python manage.py seed_data
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
