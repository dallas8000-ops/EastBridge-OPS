# EastBridge Demo Script

## 1. Goal
This script helps any presenter run a consistent client-facing demo showing:
- organization-scoped access
- ingestion and intelligence data
- citation-backed assistant answers
- generated market-entry playbooks
- vendor due diligence workflows

## 2. Demo Environment Checklist
- Backend reachable (preferred): `http://localhost:8000`
- Frontend reachable (if used): `http://localhost:5173`
- Seed/demo account available
- At least one country, trade procedure, regulatory change, and evidence document present
- If OpenAI keys are missing, assistant still demonstrates graceful fallback/refusal behavior

## 3. Suggested Timeline (20-25 minutes)
1. Platform positioning (2 min)
2. Login + tenant context (3 min)
3. Regulatory + intelligence data (4 min)
4. Assistant Q&A with citations/fallback behavior (6 min)
5. Playbook generation (4 min)
6. Vendor due diligence records (4 min)
7. Wrap-up and roadmap (2 min)

## 4. Live Walkthrough

### Step 1: Positioning (Narrative)
Say:
"EastBridge reduces market-entry risk for EU operators in East Africa by combining official-source ingestion, evidence-grounded AI answers, and operational workflows for compliance and vendors."

### Step 2: Auth and Organization Context
- Sign in with the demo account.
- Open a data view that is organization-scoped (for example vendors or playbooks).
- Mention that access is tied to JWT auth plus active organization context.

Validation point:
- Data shown belongs to the selected organization context only.

### Step 3: Data Foundation (Regulatory + Intelligence)
- Open regulatory changes.
- Filter by country/category/risk to show practical triage.
- Open intelligence indicators/risk snapshots and explain that snapshots are derived from ingestion jobs.

Validation point:
- Show that records include source links, timestamps, and country dimensions.

### Step 4: Assistant (Most Important Segment)
Run three prompts in order:
1) Good evidence path
- Example: "What recent customs changes affect imports into Uganda?"
- Show answer + citations.

2) Ambiguous path
- Example: "Summarize VAT compliance considerations for solar imports."
- Show grounded response using available evidence.

3) Sparse evidence path
- Example: "What is the exact 2032 licensing reform for sector X?"
- Show refusal/fallback behavior when evidence is insufficient.

Talking points:
- Answers are grounded in indexed evidence.
- No-key / API-failure paths still return safe deterministic behavior.
- Retrieval method metadata shows how answer was produced.

### Step 5: Playbook Generation
- Generate a playbook with origin country, industry, and target market.
- Show generated steps and source enrichment.
- Mark one checklist step complete.

Validation point:
- Explain this is operational guidance linked to evidence/trade procedure context.

### Step 6: Vendor Due Diligence
- Create or open a vendor.
- Add contract and payment records.
- Upload a sample document.

Validation point:
- Show this extends from intelligence into execution controls.

## 5. Optional API-Only Backup Demo
If UI fails, run backend endpoints directly (Postman/curl):
- `POST /api/v1/auth/login/`
- `GET /api/v1/regulatory/changes/`
- `GET /api/v1/intelligence/indicators/`
- `POST /api/v1/assistant/queries/ask/`
- `POST /api/v1/playbooks/generate/`
- `GET /api/v1/vendors/`

## 6. Common Questions and Suggested Responses
- "What happens if OpenAI is unavailable?"
  - "Assistant falls back safely: deterministic synthesis when evidence exists, and explicit refusal when evidence is insufficient."

- "How do you avoid hallucinations?"
  - "Responses are evidence-grounded with citations. Missing evidence triggers refusal instead of fabrication."

- "Is this multi-tenant?"
  - "Yes. Organization-scoped data access is enforced across key workflows."

## 7. Demo Reset Plan
Before each demo:
- Verify server health and login path.
- Confirm at least one evidence-backed assistant prompt works.
- Confirm one no-evidence prompt shows refusal behavior.
- Ensure sample vendor/playbook objects exist.

## 8. Closing Message
"EastBridge is not a generic chatbot. It is a compliance and market-entry operating layer: ingest official signals, surface risk, answer with citations, and drive execution through playbooks and vendor controls."
