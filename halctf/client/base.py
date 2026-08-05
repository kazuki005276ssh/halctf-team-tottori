"""クライアント層の共通型とインターフェース。

API 仕様が未確定なので、ここを抽象境界にする。
実クライアント（OpenAICompatClient）もモック（MockClient）も同じ Protocol を満たす。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    # assistant がツールを呼ぶ場合に格納
    tool_calls: list[ToolCall] = field(default_factory=list)
    # role == "tool" のとき、どの呼び出しへの結果か
    tool_call_id: str | None = None
    name: str | None = None

    def to_openai(self) -> dict[str, Any]:
        msg: dict[str, Any] = {"role": self.role, "content": self.content}
        if self.tool_calls:
            msg["tool_calls"] = [tc.to_openai() for tc in self.tool_calls]
        if self.tool_call_id:
            msg["tool_call_id"] = self.tool_call_id
        if self.name:
            msg["name"] = self.name
        return msg


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]

    def to_openai(self) -> dict[str, Any]:
        import json

        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.name, "arguments": json.dumps(self.arguments)},
        }


@dataclass
class ToolSpec:
    """OpenAI function-calling 形式のツール定義。"""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON Schema

    def to_openai(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


@dataclass
class ChatResult:
    """1 回の推論結果。"""

    content: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str | None = None
    finish_reason: str | None = None


class LLMClient(Protocol):
    """モデル呼び出しの最小インターフェース。"""

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        **kwargs: Any,
    ) -> ChatResult: ...
