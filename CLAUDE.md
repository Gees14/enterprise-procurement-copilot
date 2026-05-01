# Enterprise Procurement Copilot — Project Context

## What this project is

A production-style Generative AI portfolio project. Full-stack RAG + agent tool use application for procurement teams. Uses Gemini (with MockProvider fallback), FastAPI, PostgreSQL, ChromaDB, React.

Goal: serious enterprise AI project for GitHub portfolio and resume. Not a tutorial chatbot.

## Tech stack

- Backend: Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, ChromaDB, Sentence Transformers, Google Gemini
- Frontend: React 18, TypeScript, Vite, Tailwind CSS, React Router
- DevOps: Docker Compose, GitHub Actions CI, Makefile

## Architecture summary

```
User → FastAPI → ProcurementAgent
                   ├── intent detection (rule-based)
                   ├── tools (PostgreSQL: suppliers, POs, UNSPSC)
                   ├── RAG (ChromaDB via Sentence Transformers)
                   └── LLM (GeminiProvider or MockProvider)
```

Full architecture: see `docs/architecture.md`

## Development phases

### ✅ Phase 1 — COMPLETE
**Scaffold: project structure, backend skeleton, frontend skeleton**

Delivered:
- Full folder structure (backend/frontend/data/docs)
- `docker-compose.yml` with PostgreSQL + ChromaDB + backend + frontend
- `.env.example`, `.gitignore`, `Makefile`
- Backend: `main.py`, `core/` (config, logging, security/RBAC), `db/` (models, database, seed), `schemas/`, `services/` (llm_provider, supplier_service, po_service, classification_service, governance_service), `rag/` (chunking, embeddings, vector_store, retrieval, ingestion), `agents/` (procurement_agent, tools, prompts, trace)
- Frontend: `App.tsx` with routing, 4 pages (Dashboard, Copilot, Suppliers, Documents), API client layer, TypeScript types
- Sample data: 15 suppliers, 25 POs, 22 UNSPSC categories (CSV)
- Policy documents: supplier_approval_policy.md, purchase_order_policy.md, data_governance_policy.md
- Tests: test_health, test_chunking, test_governance, test_llm_provider
- Docs: architecture.md, api_contract.md, agent_design.md, evaluation.md, cloud_deployment_notes.md
- CI: .github/workflows/ci.yml

Key design decisions from Phase 1:
- MockProvider fallback when GEMINI_API_KEY is empty (important for CI and GitHub reviewers)
- Rule-based intent detection in ProcurementAgent (reliable and traceable for MVP)
- ChromaDB via HTTP client (runs in Docker, no local file conflicts)
- Governance layer (GovernanceService) handles grounding status and disclaimers
- Chat state lifted to App.tsx so conversation persists across navigation

---

### ✅ Phase 2 — COMPLETE
**Database, structured data APIs, seed validation**

Goal: make `GET /suppliers`, `GET /purchase-orders`, `GET /purchase-orders/analytics` fully work end-to-end with real PostgreSQL data.

Delivered:
- Fixed `data/sample_unspsc_categories.csv` — keywords field was unquoted (commas broke DictReader for all 22 rows, only "bolt" was read instead of full keyword list)
- Fixed `backend/app/db/seed.py` — added `DATA_DIR` env var support; 4-parent path resolves to `/` in Docker but `/app/data` is the mounted data volume
- Fixed `docker-compose.yml` — added `DATA_DIR: /app/data` to backend environment
- Added `backend/tests/conftest.py` — shared SQLite in-memory `db` fixture (StaticPool, no PostgreSQL needed)
- Added `backend/tests/test_supplier_service.py` — 14 tests covering list/filter/pagination/detail/profile-dict
- Added `backend/tests/test_purchase_order_service.py` — 18 tests covering list/filter/analytics/agent-tools

Docker Compose startup sequence confirmed correct: db (healthcheck) → chromadb (healthcheck) → backend (seed then uvicorn) → frontend

---

### ✅ Phase 3 — COMPLETE
**RAG ingestion and retrieval**

Goal: make document ingestion work end-to-end. Policy documents searchable via ChromaDB.

Delivered:
- Fixed `backend/app/rag/ingestion.py` — same `POLICY_DOCS_DIR` path bug as seed.py (resolves to `/data/policy_documents` in Docker instead of `/app/data/policy_documents`); fixed with `DATA_DIR` env var
- Upgraded `backend/app/services/classification_service.py` — split into `_classify_by_keyword()` + `_classify_by_embedding()` fallback; embedding path uses `embed_query` + `embed_texts` with cosine similarity (dot product of normalised vectors); lazy import keeps keyword-only path free of model load; threshold: 0.30 cosine similarity
- Added `backend/tests/conftest.py` — injects MagicMock stubs for `sentence_transformers`, `chromadb`, `google.generativeai` via `sys.modules.setdefault` so all test files can import RAG modules without Docker
- Added `backend/tests/test_retrieval.py` — 11 tests: source chunk shape, min_score filter, top_k passthrough, excerpt truncation at 400 chars; ChromaDB and embeddings fully mocked
- Added `backend/tests/test_classification_service.py` — 16 tests: keyword matching (case-insensitive, multi-keyword ranking, confidence cap), embedding fallback (highest cosine wins, low score → unclassified, method label, embed_texts call count)

All 79 tests pass locally without PostgreSQL, ChromaDB, or sentence_transformers installed.

---

### ✅ Phase 4 — COMPLETE
**Agent integration: full chat pipeline working**

Goal: `POST /chat` returns grounded answers end-to-end with all intents working.

Delivered:
- Added RBAC enforcement in `procurement_agent.py` for `email_draft` intent: checks `GovernanceService.check_access(role, "email_draft")` before calling any tool — analyst role gets an "Access denied" response with `grounding_status="not_grounded"` and empty `tools_called`
- Added `backend/tests/test_agent.py` — 34 tests across 4 classes:
  - `TestIntentDetection` (13): direct unit tests on `_detect_intent()` for all 6 intents + fallback
  - `TestAgentIntentRouting` (12): full `agent.run()` with mocked tools + AsyncMock LLM; validates correct tool names in `tools_called`, trace content, model_used
  - `TestGroundingStatus` (5): verifies grounding logic — classify/top_suppliers=partially_grounded, supplier_detail+RAG=grounded, policy_query+empty_RAG=partially_grounded
  - `TestGovernanceRBAC` (4): analyst denied for email_draft (no tools called, trace contains "Access denied"), manager and admin allowed

Bug fixed during testing: "Give me a summary of SUP-001" triggers `supplier_detail_with_po` (not `supplier_detail`) because "summary" is in the keyword list — tests use unambiguous questions like "Tell me about SUP-001"

All 113 tests pass locally without PostgreSQL, ChromaDB, or any API keys.

---

### ✅ Phase 5 — COMPLETE
**Frontend integration**

Goal: all 4 pages functional with real backend data.

Delivered:
- Dashboard: loads `GET /purchase-orders/analytics` + `GET /suppliers`, renders KPI cards, top suppliers, spend by category
- Copilot: full chat pipeline — sends `POST /chat`, renders grounded answers with GroundingBadge, agent trace side panel, top-k selector; chat state persists across navigation (lifted to App.tsx)
- Suppliers: loads `GET /suppliers?limit=100`, client-side filter by name/country/ID, color-coded risk and status badges
- Documents: loads `GET /documents`, ingest-sample via `POST /documents/ingest-sample`, upload via `POST /documents/upload`
- Fixed TypeScript: removed unused `RiskBadge` from `Dashboard.tsx` (was defined but not used — `noUnusedLocals: true`)
- Fixed `Suppliers.tsx` useEffect: added `.catch(() => {}).finally(...)` for error safety
- `npx tsc --noEmit` → 0 errors
- `npm run build` → clean build (40 modules, 184 kB JS / 59 kB gzip)

Key design decisions from Phase 5:
- `VITE_API_URL` env var controls backend URL; defaults to `http://localhost:8000` for local dev
- `vite.config.ts` proxy (`/api → backend:8000`) is available for Docker-internal routing if needed
- `GroundingBadge` handles all 4 statuses: grounded / partially_grounded / not_grounded / mock
- `ChatMessage.response` carries full `ChatResponse` for per-message source count, latency, trace toggle

---

### ✅ Phase 6 — COMPLETE
**Evaluation, final tests, CI green, documentation polish**

Delivered:
- Written `backend/app/evaluation/rag_eval.py` — async runner over 8 test questions; measures intent accuracy, tool accuracy, retrieval hit rate, avg latency; uses MockProvider automatically when no GEMINI_API_KEY set
- `test_questions.json` already existed from Phase 1 scaffold — verified correct expected_intent, expected_tools, expected_sources for all 8 questions
- GitHub Actions CI: backend tests (pytest 113 tests) + ruff lint + frontend type-check + build — all jobs defined and expected green
- README polished: added full 9-file test suite table, added Evaluation section with run instructions and expected metrics table
- Screenshots section already present as placeholder

Expected evaluation results (MockProvider):
- Intent accuracy: 8/8 (100%) — rule-based _detect_intent is deterministic
- Tool accuracy: 8/8 (100%) — intent→tools mapping is fixed
- Retrieval hit rate: 5/5 RAG questions (100%) — ChromaDB must be seeded
- Avg latency: < 100 ms with MockProvider

---

## Important patterns and conventions

### MockProvider
- Always returns deterministic `[MOCK]` prefixed strings
- No API key needed for local dev or CI
- Controlled by `settings.use_mock_llm` (true when `GEMINI_API_KEY` is empty)

### RBAC / Governance
- UserRole enum: analyst, manager, admin (in `app/core/security.py`)
- GovernanceService checks permissions and assigns grounding status
- Grounding: "grounded" = sources + tools, "partially_grounded" = one of them, "not_grounded" = neither

### Agent intent routing
- Intent detection in `_detect_intent()` in `procurement_agent.py`
- SUP-xxx pattern detected via regex `_SUPPLIER_ID_RE`
- RAG is always run for: policy_query, general_query, email_draft, supplier_detail
- RBAC enforced before tool dispatch: `email_draft` checks `check_access(role, "email_draft")` — analyst is denied; manager and admin are allowed
- Caution: keywords like "summary", "overview", "risk", "po" in a question containing SUP-xxx trigger `supplier_detail_with_po` (not `supplier_detail`)

### DB session pattern
- FastAPI routes use `Depends(get_db)` for session injection
- Agent tools use `SessionLocal()` directly (not in FastAPI context)
- Always close session in finally block

### ChromaDB
- HttpClient connects to `CHROMA_HOST:CHROMA_PORT`
- Collection name from `settings.chroma_collection`
- Score = 1.0 - cosine_distance (higher = more similar)
- min_score filter at 0.35 in retrieval.py

## Running locally

```bash
# Full stack
make up          # starts postgres + chromadb + backend + frontend
make seed        # seed database (also runs on startup)

# Backend only (no Docker)
cd backend
pip install -r requirements.txt
DATABASE_URL=sqlite:///./test.db uvicorn app.main:app --reload

# Tests
make test        # inside Docker
cd backend && pytest tests/ -v  # local
```

## GitHub repo

https://github.com/Gees14/enterprise-procurement-copilot

## Test suite summary (as of Phase 4)

113 tests — all pass locally without PostgreSQL, ChromaDB, sentence_transformers, or any API keys.

| File | Tests | What it covers |
|------|-------|---------------|
| test_health.py | 1 | FastAPI health endpoint |
| test_chunking.py | 4 | Text chunking with overlap |
| test_governance.py | 8 | RBAC access control + grounding status |
| test_llm_provider.py | 4 | MockProvider deterministic output |
| test_supplier_service.py | 14 | SupplierService list/filter/detail/profile-dict |
| test_purchase_order_service.py | 21 | POService list/filter/analytics/agent-tools |
| test_retrieval.py | 11 | RAG retrieval: score filter, top_k, excerpt truncation |
| test_classification_service.py | 16 | Keyword + embedding classification |
| test_agent.py | 34 | Intent detection, tool routing, grounding, RBAC |
