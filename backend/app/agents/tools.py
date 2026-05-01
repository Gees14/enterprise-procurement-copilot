"""
Procurement agent tools — each tool wraps a service call and returns a
plain dict that can be serialized for the LLM prompt and the API trace.
"""
from __future__ import annotations
from app.db.database import SessionLocal
from app.services.supplier_service import SupplierService
from app.services.purchase_order_service import PurchaseOrderService
from app.services.classification_service import ClassificationService
from app.schemas.chat import ToolCall
from app.rag.retrieval import retrieve


def tool_retrieve_policy_documents(query: str, top_k: int = 5) -> tuple[list, ToolCall]:
    sources = retrieve(query, top_k=top_k)
    call = ToolCall(
        name="retrieve_policy_documents",
        input={"query": query, "top_k": top_k},
        output_summary=f"Retrieved {len(sources)} policy chunks",
    )
    return sources, call


def tool_get_supplier_profile(supplier_id: str) -> tuple[dict | None, ToolCall]:
    db = SessionLocal()
    try:
        svc = SupplierService(db)
        data = svc.get_supplier_profile_dict(supplier_id)
    finally:
        db.close()

    summary = f"Supplier {supplier_id} found." if data else f"Supplier {supplier_id} not found."
    call = ToolCall(
        name="get_supplier_profile",
        input={"supplier_id": supplier_id},
        output_summary=summary,
    )
    return data, call


def tool_get_purchase_orders_by_supplier(
    supplier_id: str, limit: int = 10
) -> tuple[list[dict], ToolCall]:
    db = SessionLocal()
    try:
        svc = PurchaseOrderService(db)
        data = svc.get_po_by_supplier(supplier_id, limit=limit)
    finally:
        db.close()

    call = ToolCall(
        name="get_purchase_orders_by_supplier",
        input={"supplier_id": supplier_id, "limit": limit},
        output_summary=f"Found {len(data)} purchase orders for {supplier_id}",
    )
    return data, call


def tool_get_top_suppliers_by_spend(limit: int = 5) -> tuple[list[dict], ToolCall]:
    db = SessionLocal()
    try:
        svc = PurchaseOrderService(db)
        data = svc.get_top_suppliers_by_spend(limit=limit)
    finally:
        db.close()

    call = ToolCall(
        name="get_top_suppliers_by_spend",
        input={"limit": limit},
        output_summary=f"Top {len(data)} suppliers by total spend",
    )
    return data, call


def tool_classify_unspsc_item(description: str) -> tuple[dict, ToolCall]:
    db = SessionLocal()
    try:
        svc = ClassificationService(db)
        result = svc.classify(description)
    finally:
        db.close()

    call = ToolCall(
        name="classify_unspsc_item",
        input={"description": description},
        output_summary=f"Classified as: {result.category_name} (confidence {result.confidence})",
    )
    return result.model_dump(), call


def tool_generate_supplier_followup_email(
    supplier_name: str, issue: str
) -> tuple[str, ToolCall]:
    # The LLM will actually draft this — here we format context for the prompt
    context = (
        f"Supplier: {supplier_name}\n"
        f"Issue requiring follow-up: {issue}\n"
        "Draft a professional, concise follow-up email (3 paragraphs max)."
    )
    call = ToolCall(
        name="generate_supplier_followup_email",
        input={"supplier_name": supplier_name, "issue": issue},
        output_summary="Email draft context prepared for LLM generation",
    )
    return context, call
