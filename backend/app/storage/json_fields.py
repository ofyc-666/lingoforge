"""SQLite JSON 字段读写工具。

为 repository 和其他确定性服务提供最小 JSON 字段处理工具，
避免各模块重复手写 json.dumps / json.loads。
"""

from __future__ import annotations

import json
from typing import Any


def to_json_text(value: Any) -> str:
    """将 Python 值转为稳定 JSON 文本，中文不转义。

    支持 dict、list、str、int、float、bool、None。
    """
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def from_json_text(text: str | None, default: Any = None) -> Any:
    """从 JSON 文本解析对象。

    空值或无效 JSON 返回 default，不抛出未处理异常。
    """
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default
