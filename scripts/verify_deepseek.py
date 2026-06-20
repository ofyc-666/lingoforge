"""Verify the real DeepSeek provider with the local .env configuration.

This script does not print the API key. It only sends a tiny chat request
through the project's Provider Adapter and reports whether the provider works.
"""

from __future__ import annotations

import sys
from dataclasses import replace
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_BACKEND = _HERE.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from app.config import load_settings  # noqa: E402
from app.llm.factory import create_llm_provider  # noqa: E402
from app.llm.provider import LLMProviderError  # noqa: E402
from app.llm.types import LLMMessage  # noqa: E402


def main() -> int:
    loaded = load_settings()
    settings = replace(
        loaded,
        llm_mode="real",
        llm_provider="deepseek",
        deepseek_thinking_enabled=False,
    )

    if not settings.deepseek_api_key:
        print("DeepSeek 验证失败：请先在项目根目录 .env 中填写 DEEPSEEK_API_KEY。")
        print("提示：复制 .env.example 为 .env 后，只把 DEEPSEEK_API_KEY 填成你的真实 Key。")
        return 2

    try:
        provider = create_llm_provider(settings)
        response = provider.generate(
            [
                LLMMessage(
                    role="user",
                    content="请只回复 OK，用于验证 LingoForge 的 DeepSeek Provider 连通性。",
                )
            ],
            timeout_seconds=20.0,
        )
    except LLMProviderError as exc:
        code = getattr(exc, "code", exc.__class__.__name__)
        print(f"DeepSeek 验证失败：{code}")
        print(str(exc))
        return 1

    content = response.content.strip()
    print("DeepSeek 验证通过。")
    print(f"Provider: {provider.name}")
    print(f"Model: {settings.deepseek_model}")
    print(f"Response: {content[:120] or '<empty>'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
