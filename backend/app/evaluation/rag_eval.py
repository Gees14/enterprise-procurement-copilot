"""
RAG Evaluation Script — Enterprise Procurement Copilot
=======================================================
Runs 8 test questions through the full agent pipeline and reports:
  - Intent accuracy  (detected intent == expected intent)
  - Tool accuracy    (all expected tools were called)
  - Retrieval hit rate (expected source documents appeared in RAG results)
  - Average latency  (ms per question)

Usage (from backend/ directory, with Docker stack running):
    python -m app.evaluation.rag_eval

Requirements: backend stack must be reachable at DATABASE_URL and CHROMA_HOST.
MockProvider is used automatically when GEMINI_API_KEY is empty.
"""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from app.agents.procurement_agent import ProcurementAgent, _detect_intent
from app.core.logging import configure_logging, get_logger
from app.schemas.chat import ChatRequest
from app.core.security import UserRole

configure_logging()
logger = get_logger(__name__)

_QUESTIONS_PATH = Path(__file__).parent / "test_questions.json"

# ── Helpers ────────────────────────────────────────────────────────────────────

def _load_questions() -> list[dict[str, Any]]:
    with open(_QUESTIONS_PATH) as f:
        return json.load(f)


def _check_intent(detected: str, expected: str) -> bool:
    return detected == expected


def _check_tools(called_names: list[str], expected_names: list[str]) -> bool:
    """All expected tools must appear in called tools (order-independent)."""
    return all(t in called_names for t in expected_names)


def _check_retrieval(source_names: list[str], expected_sources: list[str]) -> bool:
    """All expected source documents must appear in retrieved sources."""
    if not expected_sources:
        return True
    return all(src in source_names for src in expected_sources)


# ── Evaluation runner ─────────────────────────────────────────────────────────

async def run_evaluation() -> dict[str, Any]:
    questions = _load_questions()
    agent = ProcurementAgent()

    results: list[dict[str, Any]] = []

    print(f"\n{'='*60}")
    print("  Enterprise Procurement Copilot — RAG Evaluation")
    print(f"{'='*60}\n")

    for q in questions:
        qid = q["id"]
        question = q["question"]
        expected_intent = q["expected_intent"]
        expected_tools = q["expected_tools"]
        expected_sources = q["expected_sources"]

        # Intent detection is synchronous and cheap — test it first
        detected_intent = _detect_intent(question)
        intent_ok = _check_intent(detected_intent, expected_intent)

        # Full agent run (uses MockProvider if no GEMINI_API_KEY)
        request = ChatRequest(question=question, user_role=UserRole.MANAGER, top_k=5)
        t0 = time.monotonic()
        try:
            response = await agent.run(request)
            latency_ms = int((time.monotonic() - t0) * 1000)
            error = None
        except Exception as exc:
            latency_ms = int((time.monotonic() - t0) * 1000)
            error = str(exc)
            response = None

        if response:
            called_names = [t.name for t in response.tools_called]
            source_names = [s.document_name for s in response.sources]
            tools_ok = _check_tools(called_names, expected_tools)
            retrieval_ok = _check_retrieval(source_names, expected_sources)
            grounding = response.grounding_status
        else:
            called_names = []
            source_names = []
            tools_ok = False
            retrieval_ok = False
            grounding = "error"

        result = {
            "id": qid,
            "question": question,
            "expected_intent": expected_intent,
            "detected_intent": detected_intent,
            "intent_ok": intent_ok,
            "expected_tools": expected_tools,
            "called_tools": called_names,
            "tools_ok": tools_ok,
            "expected_sources": expected_sources,
            "retrieved_sources": source_names,
            "retrieval_ok": retrieval_ok,
            "grounding_status": grounding,
            "latency_ms": latency_ms,
            "error": error,
        }
        results.append(result)

        status = "PASS" if (intent_ok and tools_ok and retrieval_ok) else "FAIL"
        print(f"[{status}] {qid}: {question[:60]}")
        if not intent_ok:
            print(f"       intent: expected={expected_intent!r} got={detected_intent!r}")
        if not tools_ok:
            print(f"       tools:  expected={expected_tools} got={called_names}")
        if not retrieval_ok:
            print(f"       sources: expected={expected_sources} got={source_names}")
        if error:
            print(f"       ERROR: {error}")
        print(f"       grounding={grounding} latency={latency_ms}ms")

    # ── Aggregate metrics ─────────────────────────────────────────────────────
    n = len(results)
    intent_acc = sum(r["intent_ok"] for r in results) / n
    tool_acc = sum(r["tools_ok"] for r in results) / n
    retrieval_hr = sum(r["retrieval_ok"] for r in results) / n
    avg_latency = sum(r["latency_ms"] for r in results) / n
    pass_count = sum(1 for r in results if r["intent_ok"] and r["tools_ok"] and r["retrieval_ok"])

    metrics = {
        "total_questions": n,
        "passed": pass_count,
        "intent_accuracy": round(intent_acc, 3),
        "tool_accuracy": round(tool_acc, 3),
        "retrieval_hit_rate": round(retrieval_hr, 3),
        "avg_latency_ms": round(avg_latency, 1),
    }

    print(f"\n{'='*60}")
    print("  Results")
    print(f"{'='*60}")
    print(f"  Questions:        {n}")
    print(f"  Passed (all 3):   {pass_count}/{n}")
    print(f"  Intent accuracy:  {intent_acc:.1%}")
    print(f"  Tool accuracy:    {tool_acc:.1%}")
    print(f"  Retrieval hit rate: {retrieval_hr:.1%}")
    print(f"  Avg latency:      {avg_latency:.0f} ms")
    print(f"{'='*60}\n")

    return {"questions": results, "metrics": metrics}


if __name__ == "__main__":
    asyncio.run(run_evaluation())
