"""shell ツール: サンドボックス内コマンド実行（Phase 2 拡張の足場）。

サンドボックス制約が未確定なので既定では無効。有効化する場合も
許可コマンドの allowlist を通す設計にする（egress / 実行時間制限に注意）。
"""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

SPEC = ToolSpec(
    name="shell",
    description="サンドボックス内でシェルコマンドを実行する。標的の探索や取得に使う。",
    parameters={
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "実行するコマンド。"},
        },
        "required": ["command"],
    },
)

# 既定の許可コマンド（実環境の制約確定後に調整）。
DEFAULT_ALLOWLIST = {"curl", "cat", "ls", "grep", "nc", "python3", "echo"}


def make_shell_tool(*, allowlist: set[str] | None = None, timeout: int = 30) -> Tool:
    allow = allowlist if allowlist is not None else DEFAULT_ALLOWLIST

    def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        command = (args.get("command") or "").strip()
        if not command:
            return ToolResult(ok=False, output="command が空です。")
        try:
            argv = shlex.split(command)
        except ValueError as e:
            return ToolResult(ok=False, output=f"コマンド解釈に失敗: {e}")
        if not argv or argv[0] not in allow:
            return ToolResult(
                ok=False, output=f"許可されていないコマンドです: {argv[0] if argv else ''}"
            )
        try:
            proc = subprocess.run(
                argv, capture_output=True, text=True, timeout=timeout
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"タイムアウト（{timeout}s）")
        out = (proc.stdout or "") + (proc.stderr or "")
        return ToolResult(ok=proc.returncode == 0, output=out[:8000])

    return Tool(SPEC, _run)
