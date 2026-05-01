# API Contract

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`

## Endpoints

### GET /health
Returns application and provider status.

**Response**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "env": "development",
  "llm_provider": "mock"
}
```

---

### POST /chat
Main copilot endpoint. Returns grounded AI answer with source citations and agent trace.

**Request**
```json
{
  "question": "What documents are required for supplier approval?",
  "user_role": "analyst",
  "top_k": 5,
  "session_id": null
}
```

**Response**
```json
{
  "answer": "According to the Supplier Approval Policy...",
  "sources": [
    {
      "document_name": "supplier_approval_policy.md",
      "chunk_id": "uuid-...",
      "excerpt": "All suppliers must submit: W-9 Form, Certificate of Insurance...",
      "score": 0.87
    }
  ],
  "tools_called": [
    {
      "name": "retrieve_policy_documents",
      "input": { "query": "supplier approval documents", "top_k": 5 },
      "output_summary": "Retrieved 4 policy chunks"
    }
  ],
  "grounding_status": "grounded",
  "trace": [
    "Detected intent: policy_query",
    "Retrieved 4 policy chunks (min score 0.72)",
    "Built LLM prompt with context",
    "Generated answer using mock-provider",
    "Grounding status: grounded"
  ],
  "latency_ms": 342,
  "model_used": "mock-provider"
}
```

**Grounding status values**
| Value | Meaning |
|-------|---------|
| `grounded` | Answer backed by retrieved docs AND structured data |
| `partially_grounded` | Answer backed by docs OR data (not both) |
| `not_grounded` | No supporting evidence found — disclaimer appended |
| `mock` | MockProvider response |

---

### GET /suppliers
Returns list of suppliers with optional filters.

**Query params:** `risk_level`, `approved` (bool), `skip`, `limit`

---

### GET /suppliers/{supplier_id}
Returns detailed supplier profile including PO metrics.

---

### GET /purchase-orders
Returns PO list. Query params: `supplier_id`, `status`, `skip`, `limit`

---

### GET /purchase-orders/analytics
Returns aggregated spend analytics.

---

### GET /documents
Returns list of ingested documents.

---

### POST /documents/ingest-sample
Ingests all policy documents from `data/policy_documents/`.

---

### POST /documents/upload
Multipart file upload. Accepts `.md`, `.txt`, `.pdf`.

---

### POST /documents/classify
Classifies an item description into UNSPSC category.

**Request:** `{ "description": "hydraulic hose assembly 3/4 inch" }`

**Response:** `{ "category_id": "31161504", "category_name": "...", "confidence": 0.72, "method": "keyword" }`
