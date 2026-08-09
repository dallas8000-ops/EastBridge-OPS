# EastBridge Ops Intelligence Architecture

## 1. System Purpose
EastBridge provides market-entry and compliance intelligence for organizations operating in East Africa. It combines structured data pipelines, document retrieval, and citation-backed assistant responses.

## 2. High-Level Components
- Backend: Django + Django REST Framework (API, auth, orchestration)
- Data Layer: SQLite locally, PostgreSQL in hosted deployments
- Async Jobs: Celery (ingestion, embedding, periodic sync)
- AI Retrieval: Hybrid keyword + embedding retrieval, optional OpenAI grounded answers
- Frontend: Vite + React client consuming `/api/v1/*`

## 3. Core Domain Apps
- `accounts`: JWT auth, registration, organization/membership context
- `core`: shared reference entities (`Country`, `DataSource`)
- `ingestion`: source fetch + normalize + dedupe pipeline, ingestion run tracking
- `trade`: EAC Trade Information Portal procedure sync and normalization
- `regulatory`: regulatory change records and alert subscriptions
- `intelligence`: economic indicators and country risk snapshots
- `assistant`: evidence store, retrieval flow, grounded Q&A, citations
- `playbooks`: generated market-entry playbooks enriched by evidence/trade procedures
- `vendors`: vendor due diligence records, documents, contracts, payments

## 4. Request and Security Model
- Authentication: `rest_framework_simplejwt` access/refresh tokens
- Authorization: organization context from `X-Organization-ID` header or membership fallback
- Multi-tenant behavior: organization-scoped queries for vendor, alerts, playbooks, and assistant history
- Hosted safety: when Railway env vars are detected, `DEBUG` defaults to `False`

## 5. Data Ingestion Pipeline
1. A scheduled task selects active `DataSource` records.
2. Source-specific fetchers return normalized `FetchedItem` objects.
3. Items are deduplicated in `IngestedItem` using `(data_source, external_id)` and content hash.
4. `EvidenceDocument` is created/updated for retrieval.
5. Regulatory sources also create/update `RegulatoryChange` entries.
6. Embeddings are generated for evidence.
7. `IngestionRun` stores batch stats and summary for observability.

## 6. Retrieval and Embedding Pipeline (Differentiator)
EastBridge uses a layered retrieval design:
- Provider resolution:
  - `fastembed` preferred in auto mode when available
  - OpenAI embeddings used when configured
  - deterministic hash fallback always available
- Embedding persistence:
  - JSON embedding in `assistant_evidencedocument.embedding`
  - optional pgvector column support for PostgreSQL (`embedding_vector`)
- Search strategy (`search_evidence`):
  - pgvector cosine search when pgvector column exists
  - otherwise hybrid score = weighted keyword relevance + cosine similarity from JSON embeddings
- Retrieval output:
  - top matches + retrieval method label (e.g., `pgvector+openai`, `hybrid+hash`, `keyword`)

## 7. Assistant Answer Generation
`POST /api/v1/assistant/queries/ask/` flow:
1. Validate question and optional country code.
2. Retrieve evidence documents via hybrid/pgvector search.
3. If no evidence: return refusal with explicit reason and remediation hint.
4. If evidence exists: create `Citation` rows with excerpts and relevance.
5. Attempt grounded LLM answer (OpenAI chat) when configured.
6. If LLM unavailable or fails: deterministic synthesis fallback.
7. Persist `AssistantQuery` with method metadata and citations.

Key guarantee: assistant responses are citation-backed and degrade gracefully when AI services are unavailable.

## 8. Playbook Generation
Playbooks blend templates with live context:
- baseline steps from industry-specific templates
- enrichment from matched evidence and trade procedures
- organization ownership for multi-tenant isolation
- patch endpoint allows checklist progress (`is_completed`) updates only

## 9. External Integrations
- OpenAI API: optional embeddings + optional grounded chat completion
- World Bank API: economic indicators and country-profile evidence
- EAC TIP and fallback datasets: trade procedures
- Optional webhooks/email for regulatory change alert dispatch

## 10. Operational Flow
- Local: Django server + SQLite + optional Celery worker
- Hosted: Railway + PostgreSQL (+ optional Redis for Celery)
- CI gates:
  - Django check
  - migration smoke (`makemigrations --check` + `migrate`)
  - backend tests with `coverage run` and `coverage report --fail-under=30`
  - fixture integrity and frontend build

## 11. Design Principles
- Evidence-first outputs over speculative AI responses
- Deterministic fallbacks for all AI-dependent paths
- Organization-scoped APIs by default
- Incremental sync with explicit run logs and counts
- API-first backend with independently deployable frontend
