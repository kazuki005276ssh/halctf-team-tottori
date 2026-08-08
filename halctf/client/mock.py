"""モックモデル（外部 API 不要のローカル検証用）。

実 LLM の代わりに、会話履歴を見て「偵察 → 攻略 → フラグ提出」を
決め打ちで進める簡易ポリシー。ReAct ループとツール層の結合を
外部依存なしで end-to-end 検証するための足場。
"""

from __future__ import annotations

import re

from halctf.client.base import ChatMessage, ChatResult, ToolCall, ToolSpec

_FLAG_RE = re.compile(r"flag\{[^}]+\}")


class MockClient:
    """定石どおりに手を進める台本ベースのモック。"""

    def __init__(self, models: list[str] | None = None) -> None:
        self.models = models or ["mock-3B"]
        self._counter = 0

    def close(self) -> None:  # インターフェース互換
        pass

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        **kwargs: object,
    ) -> ChatResult:
        self._counter += 1
        tool_names = {t.name for t in (tools or [])}

        # 直近の tool 結果からフラグが見えたら提出する。
        flag = self._find_flag(messages)
        if flag and "flag_submit" in tool_names and not self._already_submitted(messages):
            return self._call("flag_submit", {"flag": flag}, "フラグを検出したので提出する")

        # 環境変数フラグ型（read_env が使える）なら env を読む。
        if "read_env" in tool_names and not self._used(messages, "read_env"):
            name = self._env_name(messages) or "FLAG_1"
            return self._call("read_env", {"name": name}, f"環境変数 {name} を読む")

        # まだ recon していなければ偵察する。
        if "recon" in tool_names and not self._used(messages, "recon"):
            return self._call("recon", {"target": "default"}, "まず標的を偵察する")

        # recon 済みで未 exploit なら攻略を試す。
        # 偵察所見に technique='...' のヒントがあれば拾う（小型モデルの読解を模倣）。
        if "exploit" in tool_names and not self._used(messages, "exploit"):
            technique = self._suggested_technique(messages) or "default"
            return self._call(
                "exploit",
                {"target": "default", "technique": technique},
                f"偵察結果から technique={technique} で攻略を試す",
            )

        # 手詰まり: テキストで終了。
        return ChatResult(content="これ以上の手が見つからない。", model=self.models[0])

    def _call(self, name: str, args: dict, thought: str) -> ChatResult:
        return ChatResult(
            content=thought,
            tool_calls=[ToolCall(id=f"call_{self._counter}", name=name, arguments=args)],
            model=self.models[0],
        )

    @staticmethod
    def _used(messages: list[ChatMessage], name: str) -> bool:
        return any(
            tc.name == name for m in messages for tc in m.tool_calls
        )

    @staticmethod
    def _already_submitted(messages: list[ChatMessage]) -> bool:
        return MockClient._used(messages, "flag_submit")

    @staticmethod
    def _env_name(messages: list[ChatMessage]) -> str | None:
        pat = re.compile(r"\b(FLAG_\d+|BONUS_FLAG|[A-Z][A-Z0-9_]{2,}FLAG)\b")
        for m in messages:
            if m.content:
                found = pat.search(m.content)
                if found:
                    return found.group(1)
        return None

    @staticmethod
    def _suggested_technique(messages: list[ChatMessage]) -> str | None:
        hint = re.compile(r"technique='([^']+)'")
        for m in reversed(messages):
            if m.role == "tool" and m.content:
                found = hint.search(m.content)
                if found:
                    return found.group(1)
        return None

    @staticmethod
    def _find_flag(messages: list[ChatMessage]) -> str | None:
        for m in reversed(messages):
            if m.role == "tool" and m.content:
                found = _FLAG_RE.search(m.content)
                if found:
                    return found.group(0)
        return None
