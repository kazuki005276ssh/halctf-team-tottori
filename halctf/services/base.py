"""services 層の型とインターフェース。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Challenge:
    id: str
    name: str = ""
    category: str = ""
    description: str = ""
    points: int | None = None
    solved: bool = False
    attempts_remaining: int | None = None
    # get_challenge が返す追加情報（標的 URL など）をそのまま保持
    extra: dict[str, Any] = field(default_factory=dict)

    def brief(self) -> str:
        """LLM に渡す簡潔なチャレンジ説明。"""
        head = f"[{self.category or '?'}] {self.name or self.id}"
        pts = f"（{self.points}pt）" if self.points is not None else ""
        return f"{head}{pts}\n{self.description}".strip()


class ChallengeService(Protocol):
    """チャレンジの探索・状態・ヒント（MCP 経由）。"""

    def list_challenges(
        self, ctf: str | None = None, category: str | None = None
    ) -> list[Challenge]: ...

    def get_challenge(self, challenge_id: str) -> Challenge: ...

    def get_challenge_status(self, challenge_id: str) -> Challenge: ...

    def request_hint(self, challenge_id: str, index: int) -> str: ...


class Submitter(Protocol):
    """フラグ提出と完了通知。"""

    def submit(self, challenge_id: str, flag: str) -> tuple[bool, str]:
        """(受理されたか, メッセージ) を返す。"""
        ...

    def done(self) -> None:
        """run を早期終了しキュー枠を解放する。"""
        ...
