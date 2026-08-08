"""flag_submit ツール: 取得したフラグを現在のチャレンジに提出する。

提出は submitter.submit(challenge_id, flag) に委譲（sidecar /submit か MCP）。
検知回避（"CAUGHT BY SOC" 対策）として、誤提出が上限に達したら深追いせず
このチャレンジを打ち切る合図を返す。
"""

from __future__ import annotations

import re
from typing import Any

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

SPEC = ToolSpec(
    name="flag_submit",
    description="発見したフラグを提出する。確信が持てるフラグが得られたときだけ呼ぶ（誤提出は避ける）。",
    parameters={
        "type": "object",
        "properties": {
            "flag": {"type": "string", "description": "提出するフラグ文字列。"},
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

    if ctx.submitter is None:
        return ToolResult(ok=False, output="提出クライアントが未設定です。")

    max_attempts = getattr(ctx.settings, "max_flag_attempts", 3) if ctx.settings else 3
    if ctx.flag_attempts >= max_attempts:
        return ToolResult(
            ok=False,
            output="誤提出が上限に達しました。総当たりは検知されるため、このチャレンジは打ち切ります。",
            done=True,
        )

    challenge_id = ctx.challenge_id or ""
    ctx.flag_attempts += 1
    accepted, message = ctx.submitter.submit(challenge_id, flag)
    if accepted:
        return ToolResult(
            ok=True,
            output=f"フラグが受理されました: {flag}",
            flag_captured=flag,
            done=True,
        )
    return ToolResult(ok=False, output=f"フラグが拒否されました（{message}）。別の手を検討する。")


TOOL = Tool(SPEC, _run)
