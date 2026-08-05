"""フラグ提出 / 完了通知クライアント。

API 仕様が未確定なので Protocol で抽象化し、実装（HTTP）とモックを分ける。
確定したらパス・スキーマを spec/ と揃えて HttpSubmitter を微修正する。
"""

from __future__ import annotations

import logging
from typing import Protocol

import httpx

logger = logging.getLogger("halctf.submit")


class Submitter(Protocol):
    def submit(self, flag: str) -> tuple[bool, str]:
        """(受理されたか, メッセージ) を返す。"""
        ...

    def complete(self) -> None:
        """completion signal を送って run を締める。"""
        ...


class MockSubmitter:
    """ローカル検証用。標的が保持する正解と照合するだけ。"""

    def __init__(self, accepted_flags: set[str]) -> None:
        self._accepted = accepted_flags
        self.submitted: list[str] = []
        self.completed = False

    def submit(self, flag: str) -> tuple[bool, str]:
        self.submitted.append(flag)
        if flag in self._accepted:
            return True, "accepted"
        return False, "incorrect flag"

    def complete(self) -> None:
        self.completed = True


class HttpSubmitter:
    """実 API 用。パスは env（spec 確定後に固定）から差し込む。"""

    def __init__(
        self,
        base_url: str,
        submit_path: str,
        completion_path: str,
        *,
        api_key: str | None = None,
        timeout_sec: float = 30.0,
    ) -> None:
        self.submit_path = submit_path
        self.completion_path = completion_path
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_sec
        )

    def submit(self, flag: str) -> tuple[bool, str]:
        try:
            resp = self._http.post(self.submit_path, json={"flag": flag})
            resp.raise_for_status()
            data = resp.json()
            # スキーマ未確定。よくある形を緩く受ける。
            accepted = bool(data.get("correct") or data.get("accepted") or data.get("success"))
            return accepted, str(data.get("message", ""))
        except httpx.HTTPError as e:
            logger.warning("フラグ提出に失敗: %s", e)
            return False, f"submit error: {e}"

    def complete(self) -> None:
        try:
            self._http.post(self.completion_path, json={"status": "done"})
        except httpx.HTTPError as e:
            logger.warning("完了通知に失敗: %s", e)
