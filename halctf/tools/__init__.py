"""ツール層: エージェントの道具と、その登録レジストリ。"""

from __future__ import annotations

from halctf.tools import exploit, flag_submit, http_get, read_env, recon
from halctf.tools.base import Tool, ToolContext, ToolRegistry, ToolResult


def default_registry() -> ToolRegistry:
    """モックデモ用の最小3ツール（recon / exploit / flag_submit）。"""
    reg = ToolRegistry()
    reg.register(recon.TOOL)
    reg.register(exploit.TOOL)
    reg.register(flag_submit.TOOL)
    return reg


def web_registry() -> ToolRegistry:
    """実 CTF 用（env フラグ + web スクレイプ）。

    read_env: 環境変数に埋め込まれたフラグ用（STARTER Flag 1）
    http_get: web 標的の偵察・攻略（STARTER Flag 2/3, Pantheon web 系）
    flag_submit: 提出
    小型モデル対策でツールは絞る。
    """
    reg = ToolRegistry()
    reg.register(read_env.TOOL)
    reg.register(http_get.TOOL)
    reg.register(flag_submit.TOOL)
    return reg


__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "default_registry",
    "web_registry",
]
