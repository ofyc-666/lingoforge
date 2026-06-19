import pytest

from app.config import Settings
from app.llm.factory import create_llm_provider
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider import LLMProviderConfigurationError
from app.llm.types import LLMMessage, LLMResponse, LLMToolCall


def test_mock_provider_returns_stable_response():
    provider = MockLLMProvider()

    response = provider.generate([LLMMessage(role="user", content="hello")])

    assert response.content == "Mock response for: hello"
    assert response.raw["mode"] == "mock"


def test_mock_provider_can_return_queued_tool_call():
    queued = LLMResponse(
        tool_calls=(LLMToolCall(id="call-1", name="get_user_profile", arguments={"user_id": 1}),)
    )
    provider = MockLLMProvider([queued])

    response = provider.generate([LLMMessage(role="user", content="plan")])

    assert response.tool_calls[0].name == "get_user_profile"
    assert response.tool_calls[0].arguments == {"user_id": 1}


def test_provider_factory_defaults_to_mock():
    provider = create_llm_provider(Settings())

    assert provider.name == "mock"


def test_provider_factory_blocks_unimplemented_deepseek():
    settings = Settings(llm_mode="real", llm_provider="deepseek")

    with pytest.raises(LLMProviderConfigurationError):
        create_llm_provider(settings)

