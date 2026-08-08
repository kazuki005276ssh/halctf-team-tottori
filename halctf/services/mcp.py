"""MCP (Model Context Protocol) 経由のチャレンジ探索 / ヒント / 提出。

MCP_ENDPOINT に JSON-RPC の tools/call を投げる（Streamable HTTP 想定）。
公開ツール: list_ctfs / list_challenges / get_challenge / get_challenge_status /
           submit_flag / request_hint / get_scoreboard / get_score_breakdown

⚠ 正確なワイヤ形式（handshake の要否・result のスキーマ）は現地で要確認。
   ズレていてもこの1ファイルの _call/_parse を直すだけで済むよう閉じ込めてある。
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from halctf.services.base import Challenge

logger = logging.getLogger("halctf.mcp")


class McpChallengeService:
    def __init__(
        self,
        endpoint: str,
        *,
        timeout_sec: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.endpoint = endpoint
        self._http = httpx.Client(timeout=timeout_sec, transport=transport)
        self._id = 0

    def close(self) -> None:
        self._http.close()

    # --- 低レベル: tools/call ---
    def _call(self, name: str, arguments: dict[str, Any] | None = None) -> Any:
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        resp = self._http.post(self.endpoint, json=payload, headers=headers)
        resp.raise_for_status()
        return self._parse_result(resp)

    @staticmethod
    def _parse_result(resp: httpx.Response) -> Any:
        """JSON-RPC / SSE いずれの応答からも result を取り出し、可能なら JSON 化。"""
        text = resp.text
        # SSE(text/event-stream) なら data: 行を拾う
        if "text/event-stream" in resp.headers.get("content-type", ""):
            for line in text.splitlines():
                if line.startswith("data:"):
                    text = line[len("data:") :].strip()
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            return text
        if isinstance(body, dict) and "error" in body:
            raise RuntimeError(f"MCP error: {body['error']}")
        result = body.get("result", body) if isinstance(body, dict) else body
        # MCP の tools/call は result.structuredContent か result.content[].text
        if isinstance(result, dict):
            if "structuredContent" in result:
                return result["structuredContent"]
            content = result.get("content")
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        try:
                            return json.loads(item["text"])
                        except (json.JSONDecodeError, KeyError):
                            return item.get("text")
        return result

    # --- 高レベル: ChallengeService ---
    def list_challenges(
        self, ctf: str | None = None, category: str | None = None
    ) -> list[Challenge]:
        args: dict[str, Any] = {}
        if ctf:
            args["ctf"] = ctf
        if category:
            args["category"] = category
        raw = self._call("list_challenges", args)
        items = raw.get("challenges", raw) if isinstance(raw, dict) else raw
        return [self._to_challenge(x) for x in (items or []) if isinstance(x, dict)]

    def get_challenge(self, challenge_id: str) -> Challenge:
        raw = self._call("get_challenge", {"challenge_id": challenge_id})
        return self._to_challenge(raw if isinstance(raw, dict) else {"id": challenge_id})

    def get_challenge_status(self, challenge_id: str) -> Challenge:
        raw = self._call("get_challenge_status", {"challenge_id": challenge_id})
        return self._to_challenge(raw if isinstance(raw, dict) else {"id": challenge_id})

    def request_hint(self, challenge_id: str, index: int) -> str:
        raw = self._call("request_hint", {"challenge_id": challenge_id, "hint_index": index})
        if isinstance(raw, dict):
            return str(raw.get("hint", raw))
        return str(raw)

    def submit_flag(self, challenge_id: str, flag: str) -> tuple[bool, str]:
        raw = self._call("submit_flag", {"challenge_id": challenge_id, "flag": flag})
        if isinstance(raw, dict):
            accepted = bool(raw.get("correct") or raw.get("accepted") or raw.get("solved"))
            return accepted, str(raw.get("message", raw))
        return False, str(raw)

    @staticmethod
    def _to_challenge(d: dict[str, Any]) -> Challenge:
        cid = str(d.get("challenge_id") or d.get("id") or d.get("name") or "")
        return Challenge(
            id=cid,
            name=str(d.get("name", d.get("title", cid))),
            category=str(d.get("category", "")),
            description=str(d.get("description", d.get("prompt", ""))),
            points=d.get("points") or d.get("value"),
            solved=bool(d.get("solved", False)),
            attempts_remaining=d.get("attempts_remaining") or d.get("remaining"),
            extra={k: v for k, v in d.items() if k not in {"description", "prompt"}},
        )
