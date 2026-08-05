"""ループの外部状態とコンテキスト圧縮。

小型モデルはコンテキスト窓が小さい。毎ターン全履歴を渡さず、
状態を外部（ここ）に保持し、LLM には直近＋要約だけを渡す。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from halctf.client.base import ChatMessage


@dataclass
class RunState:
    system_prompt: str
    task_prompt: str
    history: list[ChatMessage] = field(default_factory=list)
    step: int = 0
    # 同一手の繰り返し検出用（tool 名 + 引数のハッシュ）
    action_signatures: list[str] = field(default_factory=list)
    flag: str | None = None
    done: bool = False

    def add(self, msg: ChatMessage) -> None:
        self.history.append(msg)

    def recent_signatures(self, n: int = 3) -> list[str]:
        return self.action_signatures[-n:]

    def build_messages(self, keep_last: int = 8) -> list[ChatMessage]:
        """LLM に渡すメッセージ列を作る（履歴が長い場合は末尾のみ + 要約）。"""
        msgs: list[ChatMessage] = [
            ChatMessage(role="system", content=self.system_prompt),
            ChatMessage(role="user", content=self.task_prompt),
        ]
        if len(self.history) <= keep_last:
            msgs.extend(self.history)
            return msgs

        # 履歴が長い: 古い部分を要約テキストに畳んで直近だけ生で渡す。
        older = self.history[:-keep_last]
        summary = _summarize(older)
        msgs.append(ChatMessage(role="user", content=f"[これまでの経緯の要約]\n{summary}"))
        msgs.extend(self.history[-keep_last:])
        return msgs


def _summarize(messages: list[ChatMessage]) -> str:
    """ローカルな軽量要約（LLM を使わず、ツール入出力の要点だけ残す）。"""
    lines: list[str] = []
    for m in messages:
        if m.tool_calls:
            for tc in m.tool_calls:
                lines.append(f"- {tc.name}({tc.arguments}) を実行")
        elif m.role == "tool" and m.content:
            snippet = m.content.strip().replace("\n", " ")[:160]
            lines.append(f"  → 結果: {snippet}")
    return "\n".join(lines[-40:]) or "（特筆すべき経緯なし）"
