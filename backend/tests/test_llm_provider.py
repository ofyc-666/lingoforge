import pytest

from app.config import Settings
from app.llm.factory import create_llm_provider
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider import LLMProviderConfigurationError
from app.llm.types import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec


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


def test_queued_responses_returned_in_order():
    """预设响应按顺序返回。"""
    r1 = LLMResponse(content="first")
    r2 = LLMResponse(content="second")
    r3 = LLMResponse(content="third")
    provider = MockLLMProvider([r1, r2, r3])

    assert provider.generate([]).content == "first"
    assert provider.generate([]).content == "second"
    assert provider.generate([]).content == "third"


def test_falls_back_to_default_after_queue_exhaustion():
    """队列耗尽后回到默认 mock 响应。"""
    queued = LLMResponse(content="queued")
    provider = MockLLMProvider([queued])

    assert provider.generate([]).content == "queued"
    # 队列已空，回退到默认
    response = provider.generate([LLMMessage(role="user", content="fallback test")])
    assert response.content == "Mock response for: fallback test"


def test_default_response_records_tool_names():
    """默认响应记录传入工具名。"""
    provider = MockLLMProvider()
    tools = [
        LLMToolSpec(name="tool_a", description="desc a", parameters={}),
        LLMToolSpec(name="tool_b", description="desc b", parameters={}),
    ]
    response = provider.generate(
        [LLMMessage(role="user", content="use tools")],
        tools=tools,
    )
    assert response.raw["tool_names"] == ["tool_a", "tool_b"]


def test_default_response_records_timeout():
    """默认响应记录 timeout。"""
    provider = MockLLMProvider()
    response = provider.generate(
        [LLMMessage(role="user", content="test")],
        timeout_seconds=30.0,
    )
    assert response.raw["timeout_seconds"] == 30.0


def test_default_response_timeout_none_when_not_provided():
    """未提供 timeout 时记录 None。"""
    provider = MockLLMProvider()
    response = provider.generate([LLMMessage(role="user", content="test")])
    assert response.raw["timeout_seconds"] is None


def test_empty_tools_list_records_empty_names():
    """空工具列表记录空列表。"""
    provider = MockLLMProvider()
    response = provider.generate(
        [LLMMessage(role="user", content="no tools")],
        tools=[],
    )
    assert response.raw["tool_names"] == []


def test_provider_factory_defaults_to_mock():
    provider = create_llm_provider(Settings())

    assert provider.name == "mock"


def test_provider_factory_blocks_unimplemented_deepseek():
    settings = Settings(llm_mode="real", llm_provider="deepseek")

    with pytest.raises(LLMProviderConfigurationError):
        create_llm_provider(settings)

