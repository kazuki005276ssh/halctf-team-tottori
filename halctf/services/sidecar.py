"""sidecar (127.0.0.1:9000) 経由のフラグ提出 / 完了通知。

Help に明記された最も単純な経路:
  - フラグ提出: POST http://127.0.0.1:9000/submit
  - 早期終了 : POST http://127.0.0.1:9000/done
MCP クライアントを引き込まずに済むので、提出はこちらを既定にする。
リクエスト/レスポンスの正確なスキーマは未確定なので、緩く受ける。
"""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger("halctf.sidecar")


class SidecarClient:
    def __init__(
        self,
        base_url: str = "http://127.0.0.1:9000",
        *,
        timeout_sec: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout_sec, transport=transport
        )

    def submit(self, challenge_id: str, flag: str) -> tuple[bool, str]:
        try:
            resp = self._http.post(
                "/submit", json={"challenge_id": challenge_id, "flag": flag}
            )
            resp.raise_for_status()
            data = resp.json()
            # スキーマ未確定。よくある受理フィールドを緩く判定。
            accepted = bool(
                data.get("correct")
                or data.get("accepted")
                or data.get("success")
                or data.get("solved")
            )
            return accepted, str(data.get("message", data))
        except httpx.HTTPError as e:
            logger.warning("フラグ提出に失敗: %s", e)
            return False, f"submit error: {e}"

    def done(self) -> None:
        try:
            self._http.post("/done", json={})
        except httpx.HTTPError as e:
            logger.warning("完了通知に失敗: %s", e)

    def close(self) -> None:
        self._http.close()
