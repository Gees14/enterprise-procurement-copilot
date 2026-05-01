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

### ⬜ Phase 3 — TODO
**RAG ingestion and retrieval**

Goal: make document ingestion work end-to-end. Policy documents searchable via ChromaDB.

Tasks:
- Test `POST /documents/ingest-sample` ingests all 3 policy documents
- Verify chunk counts are reasonable (each doc should produce 10–30 chunks)
- Test `retrieval.py` returns relevant chunks for sample questions
- Add embedding-based similarity to classification_service.py (upgrade from keyword-only)
- Add test: test_retrieval.py
- Add test: test_classification_service.py
- Validate min_score threshold (currently 0.35) produces useful results

Files to create:
- `backend/tests/test_retrieval.py`
- `backend/tests/test_classification_service.py`

Note: ChromaDB must be running for these tests. Use `pytest.importorskip` or `skipif` markers if ChromaDB not available.

---

### ⬜ Phase 4 — TODO
**Agent integration: full chat pipeline working**

Goal: `POST /chat` returns grounded answers end-to-end with all intents working.

Tasks:
- Test all 6 intent types manually with real questions
- Validate trace output is accurate for each intent
- Test MockProvider responses cover all intents correctly
- Add test: test_agent.py (mock services, test intent routing)
- Add governance test: analyst cannot trigger admin-only tools
- Test `grounding_status` is correctly assigned for all cases
- Validate `tools_called` list is accurate in API response

Files to create:
- `backend/tests/test_agent.py`

Sample questions to test manually:
- "What documents are required for supplier approval?" → policy_query
- "Which suppliers had the highest purchase order volume?" → top_suppliers
- "Classify: hydraulic hose assembly" → classify_item
- "Give me a summary of supplier SUP-001" → supplier_detail
- "Draft a follow-up email for missing documents" → email_draft

---

### ⬜ Phase 5 — TODO
**Frontend integration**

Goal: all 4 pages functional with real backend data.

Tasks:
- Confirm Dashboard loads analytics and supplier data
- Confirm Copilot chat works end-to-end (send message → get response → show sources)
- Confirm Suppliers page loads and filters work
- Confirm Documents page loads, ingest-sample works, upload works
- Fix any TypeScript type errors
- Run `npx tsc --noEmit` → zero errors
- Run `npm run build` → clean build

Known items to verify:
- `import.meta.env.VITE_API_URL` works (vite-env.d.ts exists)
- Chat state persists when navigating between pages (lifted to App.tsx)
- GroundingBadge displays correctly for all 4 statuses

---

### ⬜ Phase 6 — TODO
**Evaluation, final tests, CI green, documentation polish**

Tasks:
- Write `backend/app/evaluation/rag_eval.py` script
- Run evaluation against 8 test questions in test_questions.json
- Report: intent accuracy, retrieval hit rate, tool accuracy, avg latency
- Ensure GitHub Actions CI passes (backend tests + frontend build)
- Add missing `backend/app/services/gemini_service.py` if needed (currently in llm_provider.py)
- Polish README: add real metrics from evaluation run
- Add screenshots placeholder section

Files to create:
- `backend/app/evaluation/rag_eval.py`

CI must pass before this phase is complete.

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

Not yet created. Will be at: https://github.com/Gees14/enterprise-procurement-copilot
