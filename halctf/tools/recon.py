"""recon ツール: 標的の偵察（ポート/エンドポイント/レスポンス収集）。

MVP スタブ。context.target が offer する probe を叩いて所見を返す。
実環境ではここを HTTP クライアント / ポートスキャン等に拡張する。
"""

from __future__ import annotations

from typing import Any

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

SPEC = ToolSpec(
    name="recon",
    description="標的を偵察し、到達可能なエンドポイントやレスポンスなどの所見を集める。攻略の前に最初に呼ぶ。",
    parameters={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "偵察対象の識別子。不明なら 'default'。"},
        },
        "required": ["target"],
    },
)


def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
    target = ctx.target
    if target is None:
        return ToolResult(ok=False, output="標的が未設定です。")
    findings = target.recon(args.get("target", "default"))
    ctx.scratch["recon"] = findings  # 外部状態に保持（履歴肥大を避ける）
    return ToolResult(ok=True, output=findings)


TOOL = Tool(SPEC, _run)
