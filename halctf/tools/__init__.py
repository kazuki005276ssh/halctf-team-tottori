"""ツール層: エージェントの道具と、その登録レジストリ。"""

from __future__ import annotations

from halctf.tools import exploit, flag_submit, recon
from halctf.tools.base import Tool, ToolContext, ToolRegistry, ToolResult


def default_registry() -> ToolRegistry:
    """MVP の最小 3 ツール（recon / exploit / flag_submit）を登録して返す。

    小型モデル対策としてツール数は絞る。shell 等は制約確定後に足す。
    """
    reg = ToolRegistry()
    reg.register(recon.TOOL)
    reg.register(exploit.TOOL)
    reg.register(flag_submit.TOOL)
    return reg


__all__ = ["Tool", "ToolContext", "ToolRegistry", "ToolResult", "default_registry"]
