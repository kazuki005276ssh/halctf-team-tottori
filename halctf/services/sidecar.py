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
        # orchestrator の解決が不安定なことがある（502/タイムアウト）ので数回リトライ。
        last = ""
        for attempt in range(3):
            try:
                resp = self._http.post(
                    "/submit", json={"challenge_id": challenge_id, "flag": flag}
                )
                if resp.status_code >= 500:
                    last = f"HTTP {resp.status_code}"
                    logger.warning("提出が %s（attempt=%d）リトライ", last, attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()
                # 実応答: {"status":"correct","points_awarded":1}。
                # status 値・points_awarded・ブール系フィールドのいずれかで受理判定。
                status = str(data.get("status", "")).lower()
                points = data.get("points_awarded") or data.get("points") or 0
                accepted = (
                    status in {"correct", "accepted", "solved", "success"}
                    or (isinstance(points, (int, float)) and points > 0)
                    or bool(
                        data.get("correct")
                        or data.get("accepted")
                        or data.get("success")
                        or data.get("solved")
                    )
                )
                return accepted, str(data.get("message", data))
            except httpx.HTTPError as e:
                last = str(e)
                logger.warning("フラグ提出に失敗（attempt=%d）: %s", attempt, e)
        return False, f"submit error: {last}"

    def done(self) -> None:
        # /done は orchestrator 解決失敗で 502 になりがち（主催側の不安定）。
        # 得点済みなので best-effort。短いタイムアウトで早々に諦めスロットを解放する。
        for attempt in range(2):
            try:
                resp = self._http.post("/done", json={}, timeout=5.0)
                if resp.status_code >= 500:
                    logger.warning("完了通知 HTTP %s（attempt=%d, best-effort）", resp.status_code, attempt)
                    continue
                return
            except httpx.HTTPError as e:
                logger.warning("完了通知に失敗（attempt=%d, best-effort）: %s", attempt, e)

    def close(self) -> None:
        self._http.close()
