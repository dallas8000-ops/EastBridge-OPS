# EastBridge Ops Intelligence — Changelog

Development history by phase (moved from the README). Phase 12 is the current release.

## Phase 2

- **Ingestion workers** — RSS, HTML list scrapers, World Bank API sync
- **Evidence indexing** — All ingested content indexed for assistant retrieval
- **Playbook engine** — Industry/country rule templates enriched with evidence
- **Scored retrieval** — Assistant uses ranked evidence search with citations
- **Change alerts** — Email + webhook on new `RegulatoryChange` records
- **Celery Beat** — Scheduled ingestion every 6h (regulatory) and daily (economic)

Run ingestion manually:

```bash
cd backend
python manage.py ingest --target all
python manage.py ingest --target economic
python manage.py ingest --target regulatory
```

## Phase 3

- **Semantic RAG** — hybrid keyword + cosine retrieval; pgvector on PostgreSQL
- **EAC TIP integration** — trade procedures with `--offline` fallback
- **Auth & multi-tenant** — JWT, organizations, scoped data

## Phase 4

- **Vendor CRUD** — `POST/PATCH/DELETE /api/v1/vendors/` (org-scoped)
- **Document upload** — `POST /api/v1/vendors/{id}/upload_document/`
- **Change alerts** — `GET/POST/DELETE /api/v1/regulatory/alerts/`
- **Demo data** — `python manage.py seed_demo_org` (vendors + alert subscription)
- **Production embeddings** — OpenAI, fastembed (local), hash fallback

## Phase 5

- **Vendor document UI** — upload PDFs and certificates per supplier on `/vendors`
- **Playbook auth** — generate and list playbooks require sign-in (org-scoped)
- **Saved playbooks** — previously generated playbooks load from your organization

## Phase 6

- **Ops dashboard** — trade procedure count, embedding provider, ingestion sync times on Overview
- **Country risk snapshots** — `/intelligence` shows World Bank–derived risk scores per EAC country
- **Vendor edit/delete** — inline edit verification status, risk score; delete suppliers
- **Regulatory filters** — filter changes by country and category
- **Assistant transparency** — shows retrieval method (`hybrid+openai`, `pgvector+fastembed`, etc.)

## Phase 7

- **Playbook progress** — check off steps; `PATCH /api/v1/playbooks/steps/{id}/`
- **Assistant history** — org-scoped recent queries when signed in
- **Trade filters** — filter procedures by country, activity type, and search
- **Health check** — `GET /api/v1/health/` for deploy monitoring

## Phase 8

- **LLM-grounded answers** — OpenAI synthesizes answers from retrieved evidence only (`ANSWER_PROVIDER=auto`)
- **Vendor contracts & payments** — `POST .../add_contract/`, `POST .../add_payment/` + UI on `/vendors`
- **Ops health indicator** — API/database status on Overview dashboard
- **Docker hardening** — Postgres/Redis/backend healthchecks; `DATABASE_URL` set for Compose services

## Phase 9

- **Production Docker** — frontend nginx image (`:8080`), gunicorn via `docker-compose.prod.yml`, persistent `media` volume
- **Playbook export** — download checklist as Markdown from `/playbooks`
- **Regulatory search** — full-text search on titles and impact summaries
- **CI** — GitHub Actions backend `manage.py check` + frontend build

## Phase 10

- **Auth proxy fix** — login uses same `/api/v1` path as the Vite dev proxy
- **Org switcher** — sidebar dropdown when a user belongs to multiple organizations
- **Intelligence filters** — country filter on risk snapshots and indicators
- **Regulatory risk filter** — filter by low / medium / high / critical
- **Assistant quick-picks** — one-click EAC country example questions
- **Vendor summary** — supplier count, average risk, flagged count on `/vendors`
- **Dev script** — `scripts/dev.ps1` starts backend on `:8888` + frontend on `:5173`

## Phase 11

- **Multi-org demo** — `seed_demo_org` creates Helio Solar GmbH (UG) and NordWind Energy AG (KE) for the org switcher
- **Assistant export** — download or copy grounded answers as Markdown with citations
- **Alert pause/resume** — toggle subscriptions without deleting them
- **Regulatory → alerts** — subscribe link prefills country/category from current filters
- **Org dashboard** — Overview shows vendor, alert, and query counts for the active organization
- **Assistant fix** — anonymous users can ask questions; citation scores no longer overflow SQLite

## Phase 12 (current)

- **Assistant deep links** — `/assistant?q=...&country=UG` prefills questions from Trade and Regulatory pages
- **Trade export** — download procedure checklists as Markdown
- **Cross-module actions** — “Ask assistant” on regulatory changes and trade procedures
- **Playbook delete** — `DELETE /api/v1/playbooks/{id}/` + UI remove button
- **Overview feed** — latest five regulatory changes on the dashboard
