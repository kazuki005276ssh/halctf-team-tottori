"""http_request ツール: 標的への汎用 HTTP（GET/POST/PUT…、ヘッダ・ボディ対応）。

web チャレンジ全般（SQLi は GET、XXE/deserialize は POST ボディ、JWT は
Authorization ヘッダ、SSRF は url パラメータ）を1つのツールで賄う。
小型モデル向けに既定は GET（url だけで撃てる）。検知回避で最小間隔を空ける。
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

logger = logging.getLogger("halctf.http")

SPEC = ToolSpec(
    name="http_request",
    description=(
        "標的に HTTP リクエストを送りレスポンス（ステータス・ヘッダ・本文）を得る。"
        "既定は GET（url だけでよい）。SQLi は url のクエリに仕込む。"
        "POST/PUT や XML/JSON ボディ、独自ヘッダ（Authorization 等）も送れる。"
        "robots.txt を見たいときは url 末尾を /robots.txt にする。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "完全な URL（例 http://target/search?q=...）。"},
            "method": {"type": "string", "description": "HTTP メソッド。既定 GET。"},
            "headers": {
                "type": "object",
                "description": "追加ヘッダの key-value（例 {\"Authorization\":\"Bearer ...\"}）。",
            },
            "body": {"type": "string", "description": "リクエストボディ（POST の XML/JSON 等）。"},
        },
        "required": ["url"],
    },
)

_MAX_BODY = 6000


def make_http_request_tool(*, transport: httpx.BaseTransport | None = None) -> Tool:
    client = httpx.Client(timeout=20.0, follow_redirects=True, transport=transport)

    def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = (args.get("url") or "").strip()
        if not url:
            return ToolResult(ok=False, output="url が空です。")
        method = (args.get("method") or "GET").strip().upper()
        headers = args.get("headers") or {}
        if not isinstance(headers, dict):
            headers = {}
        body = args.get("body")

        # 検知回避: 直前アクセスから最小間隔を空ける
        interval = getattr(ctx.settings, "target_min_interval_sec", 0.0) if ctx.settings else 0.0
        last = ctx.scratch.get("_last_http", 0.0)
        now = time.monotonic()
        if interval and now - last < interval:
            time.sleep(interval - (now - last))
        ctx.scratch["_last_http"] = time.monotonic()

        # ストリームで読み、サイズ上限 or 時間上限で必ず打ち切る。
        # （SSE/Streamable HTTP 等の開きっぱなし応答で本文読取がハングするのを防ぐ）
        try:
            hdrs = {str(k): str(v) for k, v in headers.items()}
            with client.stream(
                method, url, headers=hdrs,
                content=body if body is not None else None,
            ) as resp:
                keep = {"server", "location", "content-type", "www-authenticate", "set-cookie"}
                shown = {k: v for k, v in resp.headers.items() if k.lower() in keep}
                buf = bytearray()
                start = time.monotonic()
                truncated = False
                for chunk in resp.iter_bytes():
                    buf.extend(chunk)
                    if len(buf) >= _MAX_BODY or time.monotonic() - start > 15:
                        truncated = True
                        break
                status = resp.status_code
        except httpx.HTTPError as e:
            return ToolResult(ok=False, output=f"リクエスト失敗: {e}")

        text = bytes(buf[:_MAX_BODY]).decode("utf-8", errors="replace")
        note = "（打ち切り）" if truncated else ""
        out = f"HTTP {status} {shown}{note}\n{text}"
        return ToolResult(ok=status < 500, output=out)

    return Tool(SPEC, _run)


TOOL = make_http_request_tool()
