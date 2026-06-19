from __future__ import annotations

import json

import httpx
import pytest

from app.config import Settings
from app.llm.deepseek_provider import (
    DeepSeekAuthenticationError,
    DeepSeekBadResponseError,
    DeepSeekHTTPError,
    DeepSeekProvider,
    DeepSeekRateLimitError,
    DeepSeekTimeoutError,
)
from app.llm.factory import create_llm_provider
from app.llm.provider import LLMProviderConfigurationError
from app.llm.types import LLMMessage, LLMToolSpec


def _provider(handler) -> DeepSeekProvider:
    return DeepSeekProvider(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        thinking_enabled=False,
        transport=httpx.MockTransport(handler),
    )


def _chat_response(message: dict, finish_reason: str = "stop") -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chatcmpl-test",
            "model": "deepseek-v4-flash",
            "choices": [{"index": 0, "finish_reason": finish_reason, "message": message}],
            "usage": {"total_tokens": 12},
        },
    )


def test_deepseek_provider_sends_openai_compatible_tool_payload():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["auth"] = request.headers.get("Authorization")
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return _chat_response({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {"name": "get_user_profile", "arguments": "{\"include_goal\": true}"},
                }
            ],
        }, finish_reason="tool_calls")

    provider = _provider(handler)
    response = provider.generate(
        [LLMMessage(role="user", content="读取画像")],
        tools=[
            LLMToolSpec(
                name="get_user_profile",
                description="读取画像",
                parameters={"type": "object", "properties": {}, "additionalProperties": False},
            )
        ],
    )

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["auth"] == "Bearer test-key"
    assert captured["payload"]["model"] == "deepseek-v4-flash"
    assert "thinking" not in captured["payload"]
    assert captured["payload"]["tools"][0]["type"] == "function"
    assert captured["payload"]["tool_choice"] == "auto"
    assert response.tool_calls[0].name == "get_user_profile"
    assert response.tool_calls[0].arguments == {"include_goal": True}
    assert response.raw["finish_reason"] == "tool_calls"


def test_deepseek_provider_sends_tool_result_message_and_reads_final_text():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["payload"] = json.loads(request.content.decode("utf-8"))
        return _chat_response({"role": "assistant", "content": "最终回答"})

    provider = _provider(handler)
    response = provider.generate([
        LLMMessage(role="assistant", content="需要工具"),
        LLMMessage(role="tool", tool_call_id="call-1", name="get_user_profile", content="{\"ok\": true}"),
    ])

    tool_message = captured["payload"]["messages"][1]
    assert tool_message == {
        "role": "tool",
        "content": "{\"ok\": true}",
        "tool_call_id": "call-1",
    }
    assert response.content == "最终回答"
    assert response.tool_calls == ()


def test_deepseek_provider_requires_api_key():
    with pytest.raises(LLMProviderConfigurationError):
        DeepSeekProvider(
            api_key=None,
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
        )


def test_provider_factory_creates_deepseek_when_real_mode_has_key():
    provider = create_llm_provider(Settings(
        llm_mode="real",
        llm_provider="deepseek",
        deepseek_api_key="test-key",
    ))

    assert provider.name == "deepseek"


def test_deepseek_provider_maps_authentication_error():
    provider = _provider(lambda _request: httpx.Response(401, json={"error": "bad key"}))

    with pytest.raises(DeepSeekAuthenticationError):
        provider.generate([LLMMessage(role="user", content="hello")])


def test_deepseek_provider_maps_rate_limit_error():
    provider = _provider(lambda _request: httpx.Response(429, json={"error": "limited"}))

    with pytest.raises(DeepSeekRateLimitError):
        provider.generate([LLMMessage(role="user", content="hello")])


def test_deepseek_provider_maps_timeout_error():
    def handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    provider = _provider(handler)

    with pytest.raises(DeepSeekTimeoutError):
        provider.generate([LLMMessage(role="user", content="hello")])


def test_deepseek_provider_rejects_malformed_tool_arguments():
    provider = _provider(lambda _request: _chat_response({
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call-1",
                "type": "function",
                "function": {"name": "get_user_profile", "arguments": "not-json"},
            }
        ],
    }))

    with pytest.raises(DeepSeekBadResponseError):
        provider.generate([LLMMessage(role="user", content="hello")])


class TestDeepSeekHTTPErrors:
    """DeepSeek HTTP 错误映射测试。"""

    def test_400_error_maps_to_http_error(self):
        provider = _provider(lambda _request: httpx.Response(400, json={"error": "bad request"}))
        with pytest.raises(DeepSeekHTTPError):
            provider.generate([LLMMessage(role="user", content="hello")])

    def test_500_error_maps_to_http_error(self):
        provider = _provider(lambda _request: httpx.Response(500, text="internal error"))
        with pytest.raises(DeepSeekHTTPError):
            provider.generate([LLMMessage(role="user", content="hello")])


class TestDeepSeekBadResponse:
    """DeepSeek 坏响应格式映射测试。"""

    def test_missing_choices_raises_bad_response(self):
        provider = _provider(lambda _request: httpx.Response(200, json={"id": "empty", "model": "test"}))
        with pytest.raises(DeepSeekBadResponseError):
            provider.generate([LLMMessage(role="user", content="hello")])

    def test_missing_message_in_choice_raises_bad_response(self):
        provider = _provider(lambda _request: httpx.Response(
            200,
            json={"id": "test", "model": "test", "choices": [{"index": 0, "finish_reason": "stop"}]},
        ))
        with pytest.raises(DeepSeekBadResponseError):
            provider.generate([LLMMessage(role="user", content="hello")])

    def test_tool_calls_not_a_list_raises_bad_response(self):
        provider = _provider(lambda _request: httpx.Response(
            200,
            json={
                "id": "test", "model": "test",
                "choices": [{"index": 0, "finish_reason": "tool_calls", "message": {
                    "role": "assistant", "tool_calls": "not-a-list",
                }}],
            },
        ))
        with pytest.raises(DeepSeekBadResponseError):
            provider.generate([LLMMessage(role="user", content="hello")])

    def test_malformed_json_response_raises_bad_response(self):
        provider = _provider(lambda _request: httpx.Response(200, content="not valid json}"))
        with pytest.raises(DeepSeekBadResponseError):
            provider.generate([LLMMessage(role="user", content="hello")])
