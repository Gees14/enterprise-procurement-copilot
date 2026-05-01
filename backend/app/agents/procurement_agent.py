"""
Procurement Agent — intent routing + tool orchestration + grounded answer generation.

Design philosophy for MVP:
- Rule-based intent detection keeps the agent reliable and explainable.
- Each intent maps to a defined set of tools.
- LLM is used for generation only (not for tool selection in this phase).
- Trace captures every decision for governance and debugging.
"""
from __future__ import annotations
import json
import re

from app.schemas.chat import ChatRequest, ChatResponse, ToolCall
from app.agents.trace import AgentTrace
from app.agents.prompts import SYSTEM_PROMPT, build_chat_prompt
from app.agents.tools import (
    tool_retrieve_policy_documents,
    tool_get_supplier_profile,
    tool_get_purchase_orders_by_supplier,
    tool_get_top_suppliers_by_spend,
    tool_classify_unspsc_item,
    tool_generate_supplier_followup_email,
)
from app.services.llm_provider import get_llm_provider
from app.services.governance_service import GovernanceService
from app.core.logging import get_logger

logger = get_logger(__name__)

# Supplier ID pattern — e.g. SUP-001, SUP-042
_SUPPLIER_ID_RE = re.compile(r"\bSUP-\d+\b", re.IGNORECASE)


def _detect_intent(question: str) -> str:
    """
    Rule-based intent classifier. Returns the primary intent label.
    Future: replace with LLM-based intent classification.
    """
    q = question.lower()

    if any(kw in q for kw in ["classif", "unspsc", "category", "code for", "what category"]):
        return "classify_item"

    if any(kw in q for kw in ["top supplier", "highest spend", "most purchase", "largest vendor"]):
        return "top_suppliers"

    if any(kw in q for kw in ["follow-up", "follow up", "missing document", "email", "reach out"]):
        return "email_draft"

    if _SUPPLIER_ID_RE.search(question):
        if any(kw in q for kw in ["risk", "summary", "overview", "purchase order", "po"]):
            return "supplier_detail_with_po"
        return "supplier_detail"

    if any(kw in q for kw in ["policy", "rule", "procedure", "approval", "regulation", "require"]):
        return "policy_query"

    # Default: try RAG over policy docs
    return "general_query"


class ProcurementAgent:
    def __init__(self):
        self._llm = get_llm_provider()
        self._governance = GovernanceService()

    async def run(self, request: ChatRequest) -> ChatResponse:
        trace = AgentTrace()
        tools_called: list[ToolCall] = []
        sources = []
        structured_data_parts: list[str] = []

        question = request.question
        role = request.user_role

        # ── Step 1: intent detection ─────────────────────────────────────────
        intent = _detect_intent(question)
        trace.add(f"Detected intent: {intent}")
        logger.info("Agent intent: %s | role: %s", intent, role)

        # ── Step 2: tool routing by intent ───────────────────────────────────
        if intent == "classify_item":
            result, call = tool_classify_unspsc_item(question)
            tools_called.append(call)
            trace.add(f"Classified item → {result.get('category_name')} ({result.get('category_id')})")
            structured_data_parts.append(f"Classification result:\n{json.dumps(result, indent=2)}")

        elif intent == "top_suppliers":
            data, call = tool_get_top_suppliers_by_spend(limit=5)
            tools_called.append(call)
            trace.add(f"Fetched top {len(data)} suppliers by spend")
            structured_data_parts.append(f"Top suppliers by spend:\n{json.dumps(data, indent=2)}")

        elif intent in {"supplier_detail", "supplier_detail_with_po"}:
            match = _SUPPLIER_ID_RE.search(question)
            if match:
                supplier_id = match.group().upper()
                profile, call = tool_get_supplier_profile(supplier_id)
                tools_called.append(call)
                if profile:
                    trace.add(f"Fetched profile for {supplier_id}")
                    structured_data_parts.append(f"Supplier profile:\n{json.dumps(profile, indent=2)}")
                else:
                    trace.add(f"Supplier {supplier_id} not found in database")

                if intent == "supplier_detail_with_po":
                    pos, po_call = tool_get_purchase_orders_by_supplier(supplier_id, limit=10)
                    tools_called.append(po_call)
                    trace.add(f"Fetched {len(pos)} POs for {supplier_id}")
                    structured_data_parts.append(
                        f"Recent purchase orders:\n{json.dumps(pos, indent=2)}"
                    )

        elif intent == "email_draft":
            # Extract supplier context if possible
            match = _SUPPLIER_ID_RE.search(question)
            supplier_name = match.group().upper() if match else "the supplier"
            ctx, call = tool_generate_supplier_followup_email(supplier_name, issue=question)
            tools_called.append(call)
            structured_data_parts.append(ctx)
            trace.add("Prepared email draft context for LLM generation")

        # ── Step 3: RAG retrieval (always run for policy-adjacent intents) ───
        if intent in {"policy_query", "general_query", "email_draft", "supplier_detail"}:
            retrieved_sources, rag_call = tool_retrieve_policy_documents(
                question, top_k=request.top_k
            )
            tools_called.append(rag_call)
            sources = retrieved_sources
            trace.add(
                f"Retrieved {len(sources)} policy chunks "
                f"(min score {min((s.score for s in sources), default=0):.2f})"
            )

        # ── Step 4: build LLM prompt ─────────────────────────────────────────
        context_texts = [s.excerpt for s in sources]
        structured_data_str = "\n\n".join(structured_data_parts)

        prompt = build_chat_prompt(
            question=question,
            context_chunks=context_texts,
            structured_data=structured_data_str,
            role=role,
        )
        trace.add("Built LLM prompt with context")

        # ── Step 5: generate answer ───────────────────────────────────────────
        answer = await self._llm.generate(prompt=prompt, system=SYSTEM_PROMPT)
        trace.add(f"Generated answer using {self._llm.model_name}")

        # ── Step 6: governance ────────────────────────────────────────────────
        grounding = self._governance.assess_grounding(len(sources), len(tools_called))
        answer = self._governance.apply_disclaimer(answer, grounding)
        trace.add(f"Grounding status: {grounding}")

        return ChatResponse(
            answer=answer,
            sources=sources,
            tools_called=tools_called,
            grounding_status=grounding,
            trace=trace.as_list(),
            model_used=self._llm.model_name,
        )
