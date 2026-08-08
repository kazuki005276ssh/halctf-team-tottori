"""read_env ツール: 環境変数を読む。

STARTER Flag 1 のように「フラグが自分の pod の環境変数にある」タイプ用。
値をそのまま返し、LLM がフラグと判断して flag_submit に渡す。
"""

from __future__ import annotations

import os
from typing import Any

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

SPEC = ToolSpec(
    name="read_env",
    description=(
        "環境変数の値を読む。フラグが環境変数に埋め込まれたチャレンジで使う（例 FLAG_1）。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "読み取る環境変数名。"},
        },
        "required": ["name"],
    },
)


def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    name = (args.get("name") or "").strip()
    if not name:
        return ToolResult(ok=False, output="name が空です。")
    value = os.environ.get(name)
    if value is None:
        # 何が存在するかのヒント（値は出さない）
        keys = sorted(k for k in os.environ if k.startswith(("FLAG", "BONUS", "HAL")))
        return ToolResult(ok=False, output=f"{name} は未設定。候補キー: {keys}")
    return ToolResult(ok=True, output=value)


TOOL = Tool(SPEC, _run)
