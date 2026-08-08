"""ツール層の基底とレジストリ。

小型モデルでも選択を誤らないよう、ツールは少数・説明は明快に保つ。
各ツールは ToolSpec（LLM に渡す定義）と run（実行本体）を持つ。
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from halctf.client.base import ToolSpec


@dataclass
class ToolResult:
    ok: bool
    output: str
    # ループ層が拾う制御シグナル（例: フラグ提出成功で run を締める）
    flag_captured: str | None = None
    done: bool = False


# ツール実行本体: (args, context) -> ToolResult
ToolFn = Callable[[dict[str, Any], "ToolContext"], ToolResult]


@dataclass
class ToolContext:
    """ツール間で共有する実行時コンテキスト（標的・提出クライアント等）。"""

    target: Any = None
    submitter: Any = None
    settings: Any = None
    # 現在取り組んでいるチャレンジ ID（flag_submit がこれを付けて提出する）
    challenge_id: str | None = None
    # 偵察結果などの外部状態（毎ターン LLM に全部渡さないための保管場所）
    scratch: dict[str, Any] | None = None
    # 誤提出回数（検知回避のため上限を設ける）
    flag_attempts: int = 0

    def __post_init__(self) -> None:
        if self.scratch is None:
            self.scratch = {}


class Tool:
    def __init__(self, spec: ToolSpec, fn: ToolFn) -> None:
        self.spec = spec
        self.fn = fn

    @property
    def name(self) -> str:
        return self.spec.name

    def run(self, args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        return self.fn(args, ctx)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def specs(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools)
