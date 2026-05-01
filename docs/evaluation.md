# Evaluation Framework

## Overview

The evaluation module measures the quality of the RAG pipeline and agent routing across 8 test questions covering all major intent categories.

## Metrics

| Metric | Definition | Target |
|--------|-----------|--------|
| Intent accuracy | % of questions routed to correct intent | ≥ 90% |
| Retrieval hit rate | % of questions where expected source appears in top-5 | ≥ 80% |
| Tool call accuracy | % of questions where expected tools were called | ≥ 85% |
| Avg latency | Mean response time in ms | < 3,000ms |

## Running Evaluation

```bash
# Requires backend + ChromaDB + PostgreSQL running
docker compose up -d

# Ingest sample documents first
curl -X POST http://localhost:8000/documents/ingest-sample

# Run evaluation (from backend/)
python -m app.evaluation.rag_eval
```

## Test Questions

Defined in `backend/app/evaluation/test_questions.json`.

| ID | Question | Intent | Expected Source |
|----|---------|--------|----------------|
| q001 | What documents are required for supplier approval? | policy_query | supplier_approval_policy.md |
| q002 | Which suppliers had the highest PO volume? | top_suppliers | — (structured data) |
| q003 | Classify: hydraulic hose assembly | classify_item | — (UNSPSC table) |
| q004 | What does PO policy say about payment terms? | policy_query | purchase_order_policy.md |
| q005 | Summary of supplier SUP-001 with recent POs | supplier_detail_with_po | — (structured data) |
| q006 | Draft follow-up email for missing compliance docs | email_draft | supplier_approval_policy.md |
| q007 | What is the data governance policy for PO data? | policy_query | data_governance_policy.md |
| q008 | Classify: industrial safety gloves level D | classify_item | — (UNSPSC table) |

## Evaluation Output (Example)

```
=== Procurement Copilot Evaluation ===

Questions evaluated: 8
Intent accuracy:     7/8  (87.5%)
Retrieval hit rate:  5/6  (83.3%)
Tool accuracy:       7/8  (87.5%)
Avg latency:         542ms

Per-question results:
  q001 ✓ intent=policy_query  hit=True   tools=✓  latency=612ms
  q002 ✓ intent=top_suppliers hit=N/A    tools=✓  latency=280ms
  q003 ✓ intent=classify_item hit=N/A    tools=✓  latency=195ms
  q004 ✓ intent=policy_query  hit=True   tools=✓  latency=589ms
  q005 ✓ intent=supplier_with_po hit=N/A tools=✓  latency=342ms
  q006 ✗ intent=email_draft   hit=False  tools=✓  latency=701ms
  q007 ✓ intent=policy_query  hit=True   tools=✓  latency=578ms
  q008 ✓ intent=classify_item hit=N/A    tools=✓  latency=167ms
```

## Future Improvements

- Add LLM-as-judge scoring for answer quality (using Gemini to evaluate answers)
- Measure citation precision (were all cited sources relevant?)
- Add adversarial questions (out-of-scope queries that should return "not grounded")
- Track evaluation metrics over time using MLflow or a CSV log
