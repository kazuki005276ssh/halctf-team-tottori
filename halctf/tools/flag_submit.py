"""flag_submit ツール: 取得したフラグを標準 API で提出する。

提出の実体は submit 層（Submitter）に委譲。ここは LLM から呼ばれる
インターフェースと、提出結果を制御シグナルへ変換する役割に徹する。
"""

from __future__ import annotations

import re
from typing import Any

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

SPEC = ToolSpec(
    name="flag_submit",
    description="発見したフラグを提出する。フラグ文字列が確定したら必ず呼ぶ。",
    parameters={
        "type": "object",
        "properties": {
            "flag": {"type": "string", "description": "提出するフラグ文字列（例: flag{...}）。"},
        },
        "required": ["flag"],
    },
)


def extract_flag(text: str, pattern: str) -> str | None:
    """テキストからフラグを抽出する。形式は env の正規表現で差し替え可能。"""
    m = re.search(pattern, text)
    return m.group(0) if m else None


def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    flag = (args.get("flag") or "").strip()
    if not flag:
        return ToolResult(ok=False, output="flag が空です。")

    # 念のためフラグ形式を検証（誤提出でスコアを浪費しない）。
    default_pattern = r"flag\{[^}]+\}"
    pattern = default_pattern
    if ctx.settings is not None:
        pattern = getattr(ctx.settings, "flag_regex", default_pattern)
    normalized = extract_flag(flag, pattern) or flag

    if ctx.submitter is None:
        return ToolResult(ok=False, output="提出クライアントが未設定です。")

    accepted, message = ctx.submitter.submit(normalized)
    if accepted:
        return ToolResult(
            ok=True,
            output=f"フラグが受理されました: {normalized}",
            flag_captured=normalized,
            done=True,
        )
    return ToolResult(ok=False, output=f"フラグが拒否されました: {message}")


TOOL = Tool(SPEC, _run)
