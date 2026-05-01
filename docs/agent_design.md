# Agent Design

## Overview

The Procurement Agent uses a hybrid routing pattern:

1. **Rule-based intent detection** — deterministic, fast, fully traceable
2. **Tool dispatch** — each intent maps to defined tools
3. **LLM generation** — used for answer synthesis, not for tool selection (MVP)

This design is deliberately conservative. LLM-based tool selection introduces hallucination risk in tool routing. For a portfolio project demonstrating enterprise thinking, reliability and traceability take priority over autonomous flexibility.

## Intent Categories

| Intent | Trigger Keywords | Tools Called |
|--------|-----------------|-------------|
| `classify_item` | classify, unspsc, category, what category | `classify_unspsc_item` |
| `top_suppliers` | top supplier, highest spend, most purchase | `get_top_suppliers_by_spend` |
| `supplier_detail` | SUP-xxx pattern | `get_supplier_profile` |
| `supplier_detail_with_po` | SUP-xxx + risk/po/summary | `get_supplier_profile`, `get_purchase_orders_by_supplier` |
| `email_draft` | follow-up, email, missing document, reach out | `generate_supplier_followup_email`, RAG |
| `policy_query` | policy, rule, approval, require, regulation | RAG only |
| `general_query` | default fallback | RAG only |

## Tool Definitions

### `retrieve_policy_documents(query, top_k)`
Embeds the query and runs cosine similarity search against ChromaDB.
Returns chunks with source document name, excerpt, and similarity score.
Min score threshold: 0.35 (configurable).

### `get_supplier_profile(supplier_id)`
Queries PostgreSQL for supplier master data + aggregated PO metrics.
Returns: risk level, approved status, missing documents, total spend, PO count.

### `get_purchase_orders_by_supplier(supplier_id, limit)`
Returns recent POs for a supplier: ID, amount, status, date, item description.

### `get_top_suppliers_by_spend(limit)`
Aggregated query: supplier name + total PO spend, ordered descending.

### `classify_unspsc_item(description)`
Keyword-based classifier against UNSPSC category table.
Phase 3 will add embedding similarity for better accuracy.

### `generate_supplier_followup_email(supplier_name, issue)`
Prepares structured context for the LLM to draft a personalized follow-up email.

## Trace Format

Every agent run produces a trace list:
```json
[
  "Detected intent: policy_query",
  "Retrieved 4 policy chunks (min score 0.72)",
  "Built LLM prompt with context",
  "Generated answer using gemini-1.5-flash",
  "Grounding status: grounded"
]
```

Traces are returned in the API response and displayed in the frontend Trace Panel.

## Governance Integration

Before returning the answer:
1. `GovernanceService.assess_grounding()` evaluates source evidence
2. `GovernanceService.apply_disclaimer()` appends disclaimer if not grounded
3. Role permissions checked per-tool (Phase 2 enhancement)

## Future: LLM-Based Tool Selection

To upgrade to autonomous tool selection, replace `_detect_intent()` with a structured generation call:

```python
intent = await llm.generate(
    prompt=f"Question: {question}\nAvailable tools: ...\nWhich tools should be called?",
    system="Return a JSON list of tool names."
)
```

The tool dispatch and governance layers remain unchanged.
