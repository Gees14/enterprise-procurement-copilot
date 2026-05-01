"""
LLM provider abstraction layer.

GeminiProvider is used when GEMINI_API_KEY is set.
MockProvider is the default — deterministic responses for local dev and CI.
"""
from __future__ import annotations

import abc
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseLLMProvider(abc.ABC):
    """Contract that all LLM providers must satisfy."""

    @abc.abstractmethod
    async def generate(self, prompt: str, system: str = "") -> str:
        """Generate a text completion."""

    @property
    @abc.abstractmethod
    def model_name(self) -> str:
        """Human-readable model identifier for traceability."""


class MockProvider(BaseLLMProvider):
    """Deterministic stub — works without any API key."""

    @property
    def model_name(self) -> str:
        return "mock-provider"

    async def generate(self, prompt: str, system: str = "") -> str:
        logger.debug("MockProvider.generate called (no API key configured)")

        # Detect question intent for minimally useful mock answers
        q = prompt.lower()

        if "supplier" in q and ("risk" in q or "summary" in q):
            return (
                "[MOCK] Supplier risk summary: Based on available data, this supplier has "
                "MEDIUM risk level with 2 missing compliance documents. "
                "Recommend follow-up before next PO issuance."
            )
        if "policy" in q or "document" in q or "approval" in q:
            return (
                "[MOCK] Policy answer: According to the supplier approval policy, "
                "all suppliers must submit a completed W-9, insurance certificate, "
                "and signed vendor agreement before purchase orders can be issued. "
                "Missing documentation must be resolved within 30 days."
            )
        if "classif" in q or "unspsc" in q:
            return (
                "[MOCK] Classification result: The item description maps to "
                "UNSPSC category 31161500 — Hydraulic fittings and assemblies."
            )
        if "email" in q or "follow" in q:
            return (
                "[MOCK] Draft email:\n\nDear Supplier,\n\n"
                "We are reaching out regarding outstanding documentation required "
                "for your vendor account. Please submit the missing items within 15 business days "
                "to avoid disruption to active purchase orders.\n\n"
                "Best regards,\nProcurement Team"
            )
        if "top" in q and "supplier" in q:
            return (
                "[MOCK] Top suppliers by spend: Based on structured data, "
                "the top supplier this period is Acme Industrial Supplies with $850,000 in PO volume."
            )

        return (
            "[MOCK] I don't have enough information to answer this question grounded in "
            "the available documents and data. Please configure a GEMINI_API_KEY for "
            "full AI responses."
        )


class GeminiProvider(BaseLLMProvider):
    """Production provider using Google Gemini via the generativeai SDK."""

    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._model_name = model

    @property
    def model_name(self) -> str:
        return self._model_name

    async def generate(self, prompt: str, system: str = "") -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        response = self._model.generate_content(full_prompt)
        return response.text


def get_llm_provider() -> BaseLLMProvider:
    """Factory — returns GeminiProvider or MockProvider based on config."""
    settings = get_settings()
    if settings.use_mock_llm:
        logger.info("Using MockProvider (GEMINI_API_KEY not set)")
        return MockProvider()
    logger.info("Using GeminiProvider (model=%s)", settings.gemini_model)
    return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)
