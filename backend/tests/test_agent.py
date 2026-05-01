"""
Tests for ProcurementAgent — intent detection, tool routing, grounding status, RBAC.
All external services (DB, ChromaDB, LLM) are mocked.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.procurement_agent import ProcurementAgent, _detect_intent
from app.core.security import UserRole
from app.schemas.chat import ChatRequest, SourceChunk, ToolCall


# ── Mock return-value builders ─────────────────────────────────────────────────

def _rag(n: int = 2):
    chunks = [
        SourceChunk(document_name="policy.md", chunk_id=f"id-{i}", excerpt="Policy text.", score=0.8)
        for i in range(n)
    ]
    call = ToolCall(
        name="retrieve_policy_documents",
        input={"query": "q", "top_k": 5},
        output_summary=f"Retrieved {n} policy chunks",
    )
    return chunks, call


def _classify():
    result = {
        "description": "hydraulic hose assembly",
        "category_id": "31161504",
        "category_name": "Hydraulic hose assemblies",
        "confidence": 0.9,
        "method": "keyword",
    }
    call = ToolCall(
        name="classify_unspsc_item",
        input={"description": "hydraulic hose assembly"},
        output_summary="Classified as: Hydraulic hose assemblies (confidence 0.9)",
    )
    return result, call


def _top_suppliers():
    data = [{"supplier_id": "SUP-001", "supplier_name": "Acme", "total_spend": 50_000.0}]
    call = ToolCall(
        name="get_top_suppliers_by_spend",
        input={"limit": 5},
        output_summary="Top 1 suppliers by total spend",
    )
    return data, call


def _supplier_profile(sid: str = "SUP-001"):
    data = {
        "supplier_id": sid, "supplier_name": "Acme Industrial",
        "country": "USA", "risk_level": "LOW", "approved_status": True,
        "total_po_amount": 50_000.0, "po_count": 3, "open_po_count": 1,
    }
    call = ToolCall(
        name="get_supplier_profile",
        input={"supplier_id": sid},
        output_summary=f"Supplier {sid} found.",
    )
    return data, call


def _pos(sid: str = "SUP-001"):
    data = [{"po_id": "PO-001", "amount": 10_000.0, "status": "OPEN",
              "date": "2024-01-15", "item_description": "Steel", "category": "Raw Materials",
              "currency": "USD"}]
    call = ToolCall(
        name="get_purchase_orders_by_supplier",
        input={"supplier_id": sid, "limit": 10},
        output_summary=f"Found 1 purchase orders for {sid}",
    )
    return data, call


def _email(supplier_name: str = "the supplier"):
    ctx = f"Supplier: {supplier_name}\nIssue: missing docs\nDraft a professional email."
    call = ToolCall(
        name="generate_supplier_followup_email",
        input={"supplier_name": supplier_name, "issue": "missing docs"},
        output_summary="Email draft context prepared for LLM generation",
    )
    return ctx, call


# ── Fixtures ────────────────────────────────────────────────────────────────────

@pytest.fixture
def agent():
    """ProcurementAgent with a mocked LLM — no API key or Docker needed."""
    mock_llm = MagicMock()
    mock_llm.model_name = "mock-provider"
    mock_llm.generate = AsyncMock(return_value="[MOCK] Procurement copilot answer.")
    with patch("app.agents.procurement_agent.get_llm_provider", return_value=mock_llm):
        yield ProcurementAgent()


# ── Intent detection (unit tests — no agent instance needed) ───────────────────

class TestIntentDetection:
    def test_classify_by_classify_keyword(self):
        assert _detect_intent("Classify: hydraulic hose assembly") == "classify_item"

    def test_classify_by_unspsc_keyword(self):
        assert _detect_intent("What UNSPSC code does this item get?") == "classify_item"

    def test_classify_by_category_keyword(self):
        assert _detect_intent("What category does this belong to?") == "classify_item"

    def test_top_suppliers_by_highest_spend(self):
        assert _detect_intent("Which suppliers had the highest spend this year?") == "top_suppliers"

    def test_top_suppliers_by_top_supplier_phrase(self):
        assert _detect_intent("Show me the top supplier list") == "top_suppliers"

    def test_supplier_detail_by_id_only(self):
        assert _detect_intent("Tell me about SUP-001") == "supplier_detail"

    def test_supplier_detail_with_po_by_id_and_po_keyword(self):
        assert _detect_intent("SUP-042 purchase order history") == "supplier_detail_with_po"

    def test_supplier_detail_with_po_by_risk_keyword(self):
        assert _detect_intent("What is the risk profile for SUP-007?") == "supplier_detail_with_po"

    def test_email_draft_by_follow_up(self):
        assert _detect_intent("Send a follow-up for missing documents") == "email_draft"

    def test_email_draft_by_email_keyword(self):
        assert _detect_intent("Draft an email to reach out to the supplier") == "email_draft"

    def test_policy_query_by_policy_keyword(self):
        assert _detect_intent("What does the approval policy say?") == "policy_query"

    def test_policy_query_by_require_keyword(self):
        assert _detect_intent("What documents are required for onboarding a supplier?") == "policy_query"

    def test_general_query_fallback(self):
        assert _detect_intent("Hello, what can you help me with today?") == "general_query"


# ── Agent intent routing ─────────────────────────────────────────────────────────

class TestAgentIntentRouting:
    @pytest.mark.asyncio
    async def test_classify_item_calls_classify_tool(self, agent):
        with patch("app.agents.procurement_agent.tool_classify_unspsc_item", return_value=_classify()):
            response = await agent.run(
                ChatRequest(question="Classify: hydraulic hose assembly", user_role=UserRole.ANALYST)
            )
        assert "classify_unspsc_item" in [t.name for t in response.tools_called]

    @pytest.mark.asyncio
    async def test_classify_item_does_not_call_rag(self, agent):
        with patch("app.agents.procurement_agent.tool_classify_unspsc_item", return_value=_classify()):
            response = await agent.run(
                ChatRequest(question="Classify: hydraulic hose assembly", user_role=UserRole.ANALYST)
            )
        assert "retrieve_policy_documents" not in [t.name for t in response.tools_called]

    @pytest.mark.asyncio
    async def test_top_suppliers_calls_spend_tool(self, agent):
        with patch("app.agents.procurement_agent.tool_get_top_suppliers_by_spend", return_value=_top_suppliers()):
            response = await agent.run(
                ChatRequest(question="Which suppliers had the highest spend?", user_role=UserRole.MANAGER)
            )
        assert "get_top_suppliers_by_spend" in [t.name for t in response.tools_called]

    @pytest.mark.asyncio
    async def test_supplier_detail_calls_profile_and_rag(self, agent):
        with (
            patch("app.agents.procurement_agent.tool_get_supplier_profile", return_value=_supplier_profile()),
            patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(2)),
        ):
            response = await agent.run(
                ChatRequest(question="Tell me about SUP-001", user_role=UserRole.MANAGER)
            )
        tool_names = [t.name for t in response.tools_called]
        assert "get_supplier_profile" in tool_names
        assert "retrieve_policy_documents" in tool_names

    @pytest.mark.asyncio
    async def test_supplier_detail_with_po_calls_profile_and_pos(self, agent):
        with (
            patch("app.agents.procurement_agent.tool_get_supplier_profile", return_value=_supplier_profile()),
            patch("app.agents.procurement_agent.tool_get_purchase_orders_by_supplier", return_value=_pos()),
        ):
            response = await agent.run(
                ChatRequest(question="SUP-001 purchase order summary", user_role=UserRole.MANAGER)
            )
        tool_names = [t.name for t in response.tools_called]
        assert "get_supplier_profile" in tool_names
        assert "get_purchase_orders_by_supplier" in tool_names

    @pytest.mark.asyncio
    async def test_supplier_detail_with_po_does_not_call_rag(self, agent):
        with (
            patch("app.agents.procurement_agent.tool_get_supplier_profile", return_value=_supplier_profile()),
            patch("app.agents.procurement_agent.tool_get_purchase_orders_by_supplier", return_value=_pos()),
        ):
            response = await agent.run(
                ChatRequest(question="SUP-001 purchase order summary", user_role=UserRole.MANAGER)
            )
        assert "retrieve_policy_documents" not in [t.name for t in response.tools_called]

    @pytest.mark.asyncio
    async def test_policy_query_calls_rag_only(self, agent):
        with patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(3)):
            response = await agent.run(
                ChatRequest(question="What does the approval policy require?", user_role=UserRole.ANALYST)
            )
        tool_names = [t.name for t in response.tools_called]
        assert "retrieve_policy_documents" in tool_names
        assert "classify_unspsc_item" not in tool_names
        assert "get_supplier_profile" not in tool_names

    @pytest.mark.asyncio
    async def test_email_draft_calls_email_tool_and_rag(self, agent):
        with (
            patch("app.agents.procurement_agent.tool_generate_supplier_followup_email", return_value=_email()),
            patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(2)),
        ):
            response = await agent.run(
                ChatRequest(
                    question="Draft a follow-up email for missing documents",
                    user_role=UserRole.MANAGER,
                )
            )
        tool_names = [t.name for t in response.tools_called]
        assert "generate_supplier_followup_email" in tool_names
        assert "retrieve_policy_documents" in tool_names

    @pytest.mark.asyncio
    async def test_trace_includes_detected_intent(self, agent):
        with patch("app.agents.procurement_agent.tool_classify_unspsc_item", return_value=_classify()):
            response = await agent.run(
                ChatRequest(question="Classify: safety helmet", user_role=UserRole.ANALYST)
            )
        assert any("Detected intent: classify_item" in step for step in response.trace)

    @pytest.mark.asyncio
    async def test_trace_includes_grounding_status(self, agent):
        with patch("app.agents.procurement_agent.tool_classify_unspsc_item", return_value=_classify()):
            response = await agent.run(
                ChatRequest(question="Classify: safety helmet", user_role=UserRole.ANALYST)
            )
        assert any("Grounding status:" in step for step in response.trace)

    @pytest.mark.asyncio
    async def test_model_used_is_populated(self, agent):
        with patch("app.agents.procurement_agent.tool_classify_unspsc_item", return_value=_classify()):
            response = await agent.run(
                ChatRequest(question="Classify: safety helmet", user_role=UserRole.ANALYST)
            )
        assert response.model_used == "mock-provider"

    @pytest.mark.asyncio
    async def test_answer_is_non_empty_string(self, agent):
        with patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(2)):
            response = await agent.run(
                ChatRequest(question="What are the approval requirements?", user_role=UserRole.ANALYST)
            )
        assert isinstance(response.answer, str)
        assert len(response.answer) > 0


# ── Grounding status ─────────────────────────────────────────────────────────────

class TestGroundingStatus:
    @pytest.mark.asyncio
    async def test_classify_is_partially_grounded(self, agent):
        # 1 tool called, 0 RAG sources → partially_grounded
        with patch("app.agents.procurement_agent.tool_classify_unspsc_item", return_value=_classify()):
            response = await agent.run(
                ChatRequest(question="Classify: safety helmet", user_role=UserRole.ANALYST)
            )
        assert response.grounding_status == "partially_grounded"

    @pytest.mark.asyncio
    async def test_top_suppliers_is_partially_grounded(self, agent):
        with patch("app.agents.procurement_agent.tool_get_top_suppliers_by_spend", return_value=_top_suppliers()):
            response = await agent.run(
                ChatRequest(question="Who are the top suppliers by spend?", user_role=UserRole.MANAGER)
            )
        assert response.grounding_status == "partially_grounded"

    @pytest.mark.asyncio
    async def test_supplier_detail_with_rag_results_is_grounded(self, agent):
        # profile tool + RAG with chunks → sources > 0 AND tools > 0 → grounded
        with (
            patch("app.agents.procurement_agent.tool_get_supplier_profile", return_value=_supplier_profile()),
            patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(2)),
        ):
            response = await agent.run(
                ChatRequest(question="Tell me about SUP-001", user_role=UserRole.MANAGER)
            )
        assert response.grounding_status == "grounded"

    @pytest.mark.asyncio
    async def test_policy_query_with_rag_results_is_grounded(self, agent):
        with patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(3)):
            response = await agent.run(
                ChatRequest(question="What are the approval requirements?", user_role=UserRole.ANALYST)
            )
        assert response.grounding_status == "grounded"

    @pytest.mark.asyncio
    async def test_policy_query_with_empty_rag_is_partially_grounded(self, agent):
        # RAG returns 0 chunks → 1 tool but 0 sources → partially_grounded
        with patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(0)):
            response = await agent.run(
                ChatRequest(question="What are the approval requirements?", user_role=UserRole.ANALYST)
            )
        assert response.grounding_status == "partially_grounded"


# ── Governance / RBAC ────────────────────────────────────────────────────────────

class TestGovernanceRBAC:
    @pytest.mark.asyncio
    async def test_analyst_cannot_request_email_draft(self, agent):
        """Analyst lacks 'email_draft' permission — agent must deny before calling any tool."""
        response = await agent.run(
            ChatRequest(
                question="Draft a follow-up email for missing documents",
                user_role=UserRole.ANALYST,
            )
        )
        assert "Access denied" in response.answer
        assert response.grounding_status == "not_grounded"
        # No tools should have been called
        assert response.tools_called == []

    @pytest.mark.asyncio
    async def test_analyst_email_deny_is_in_trace(self, agent):
        response = await agent.run(
            ChatRequest(
                question="Send an email about missing documents",
                user_role=UserRole.ANALYST,
            )
        )
        assert any("Access denied" in step for step in response.trace)

    @pytest.mark.asyncio
    async def test_manager_can_request_email_draft(self, agent):
        """Manager has 'email_draft' permission — tool must be called."""
        with (
            patch("app.agents.procurement_agent.tool_generate_supplier_followup_email", return_value=_email()),
            patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(1)),
        ):
            response = await agent.run(
                ChatRequest(
                    question="Draft a follow-up email for missing documents",
                    user_role=UserRole.MANAGER,
                )
            )
        assert "generate_supplier_followup_email" in [t.name for t in response.tools_called]
        assert "Access denied" not in response.answer

    @pytest.mark.asyncio
    async def test_admin_can_request_email_draft(self, agent):
        with (
            patch("app.agents.procurement_agent.tool_generate_supplier_followup_email", return_value=_email()),
            patch("app.agents.procurement_agent.tool_retrieve_policy_documents", return_value=_rag(1)),
        ):
            response = await agent.run(
                ChatRequest(
                    question="Draft an email for SUP-001 regarding missing certificates",
                    user_role=UserRole.ADMIN,
                )
            )
        assert "generate_supplier_followup_email" in [t.name for t in response.tools_called]
