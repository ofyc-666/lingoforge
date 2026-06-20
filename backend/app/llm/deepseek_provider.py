from __future__ import annotations

import json
from typing import Any, Sequence

import httpx

from app.llm.provider import LLMProviderConfigurationError, LLMProviderError
from app.llm.types import LLMMessage, LLMResponse, LLMToolCall, LLMToolSpec


class DeepSeekProviderError(LLMProviderError):
    """DeepSeek Provider 的稳定错误基类。"""

    code = "DEEPSEEK_PROVIDER_ERROR"


class DeepSeekAuthenticationError(DeepSeekProviderError):
    code = "DEEPSEEK_AUTHENTICATION_FAILED"


class DeepSeekRateLimitError(DeepSeekProviderError):
    code = "DEEPSEEK_RATE_LIMITED"


class DeepSeekTimeoutError(DeepSeekProviderError):
    code = "DEEPSEEK_TIMEOUT"


class DeepSeekBadResponseError(DeepSeekProviderError):
    code = "DEEPSEEK_BAD_RESPONSE"


class DeepSeekHTTPError(DeepSeekProviderError):
    code = "DEEPSEEK_HTTP_ERROR"


class DeepSeekProvider:
    """DeepSeek OpenAI 兼容 Chat Completions Provider。"""

    name = "deepseek"

    def __init__(
        self,
        api_key: str | None,
        base_url: str,
        model: str,
        thinking_enabled: bool = False,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key:
            raise LLMProviderConfigurationError("DEEPSEEK_API_KEY is required when LLM_MODE is real.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.thinking_enabled = thinking_enabled
        self.transport = transport

    def generate(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolSpec] | None = None,
        timeout_seconds: float | None = None,
    ) -> LLMResponse:
        payload = self._build_payload(messages, tools)
        timeout = timeout_seconds if timeout_seconds is not None else 30.0
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=timeout,
                transport=self.transport,
            ) as client:
                response = client.post(
                    "/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
        except httpx.TimeoutException as exc:
            raise DeepSeekTimeoutError("DeepSeek request timed out.") from exc
        except httpx.HTTPError as exc:
            raise DeepSeekHTTPError("DeepSeek request failed.") from exc

        if response.status_code in (401, 403):
            raise DeepSeekAuthenticationError("DeepSeek authentication failed.")
        if response.status_code == 429:
            raise DeepSeekRateLimitError("DeepSeek rate limit exceeded.")
        if response.status_code >= 400:
            body_snippet = (response.text or "")[:300]
            raise DeepSeekHTTPError(
                f"DeepSeek returned HTTP {response.status_code}: {body_snippet}"
            )

        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise DeepSeekBadResponseError("DeepSeek returned malformed JSON.") from exc

        return self._parse_response(data)

    def _build_payload(
        self,
        messages: Sequence[LLMMessage],
        tools: Sequence[LLMToolSpec] | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [self._message_to_payload(message) for message in messages],
            "stream": False,
        }
        if self.thinking_enabled:
            payload["thinking"] = {"type": "enabled"}
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"
        return payload

    def _message_to_payload(self, message: LLMMessage) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "role": message.role,
            "content": message.content,
        }
        if message.name and message.role != "tool":
            payload["name"] = message.name
        if message.role == "tool":
            if not message.tool_call_id:
                raise DeepSeekBadResponseError("Tool message must include tool_call_id.")
            payload["tool_call_id"] = message.tool_call_id
        if message.tool_calls:
            payload["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.name,
                        "arguments": json.dumps(tc.arguments, ensure_ascii=False),
                    },
                }
                for tc in message.tool_calls
            ]
        return payload

    def _parse_response(self, data: dict[str, Any]) -> LLMResponse:
        try:
            choice = data["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise DeepSeekBadResponseError("DeepSeek response missing choices[0].message.") from exc

        content = message.get("content") or ""
        raw_tool_calls = message.get("tool_calls") or []
        if not isinstance(raw_tool_calls, list):
            raise DeepSeekBadResponseError("DeepSeek tool_calls must be a list.")

        tool_calls: list[LLMToolCall] = []
        for raw_tool_call in raw_tool_calls:
            try:
                function = raw_tool_call["function"]
                raw_arguments = function.get("arguments") or "{}"
                arguments = json.loads(raw_arguments)
                if not isinstance(arguments, dict):
                    raise TypeError("tool arguments must be an object")
                tool_calls.append(
                    LLMToolCall(
                        id=str(raw_tool_call["id"]),
                        name=str(function["name"]),
                        arguments=arguments,
                    )
                )
            except (KeyError, TypeError, json.JSONDecodeError) as exc:
                raise DeepSeekBadResponseError("DeepSeek response contains invalid tool call.") from exc

        return LLMResponse(
            content=content,
            tool_calls=tuple(tool_calls),
            raw={
                "provider": self.name,
                "response_id": data.get("id"),
                "model": data.get("model"),
                "finish_reason": choice.get("finish_reason"),
                "usage": data.get("usage"),
            },
        )
