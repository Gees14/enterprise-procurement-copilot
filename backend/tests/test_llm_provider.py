import pytest
from app.services.llm_provider import MockProvider


@pytest.mark.asyncio
async def test_mock_provider_returns_string():
    provider = MockProvider()
    result = await provider.generate("What is the supplier approval policy?")
    assert isinstance(result, str)
    assert len(result) > 0


@pytest.mark.asyncio
async def test_mock_provider_policy_response():
    provider = MockProvider()
    result = await provider.generate("What does the policy say about approval?")
    assert "[MOCK]" in result


@pytest.mark.asyncio
async def test_mock_provider_classify_response():
    provider = MockProvider()
    result = await provider.generate("Classify this item: hydraulic hose")
    assert "[MOCK]" in result


def test_mock_provider_model_name():
    assert MockProvider().model_name == "mock-provider"
