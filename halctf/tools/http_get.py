"""http_get ツール: 標的 URL に HTTP GET する（web チャレンジの偵察・攻略）。

STARTER Flag 2（ページをスクレイプ）/ Flag 3（robots.txt を見る）など、
web 標的を実際に叩くための最小ツール。標的は現在の CTF のサブネットにのみ
到達可能（ネットワークポリシーで制限）。

検知回避のため、連続アクセスには最小間隔を設ける（総当たり的挙動を避ける）。
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
    name="http_get",
    description=(
        "標的の URL に HTTP GET してレスポンス（ステータス・ヘッダ・本文）を得る。"
        "web チャレンジの偵察・攻略に使う。robots.txt は URL 末尾を /robots.txt にする。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "取得する完全な URL（例 http://target/robots.txt）。"},
        },
        "required": ["url"],
    },
)

_MAX_BODY = 6000


def make_http_get_tool(*, transport: httpx.BaseTransport | None = None) -> Tool:
    client = httpx.Client(timeout=20.0, follow_redirects=True, transport=transport)

    def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        url = (args.get("url") or "").strip()
        if not url:
            return ToolResult(ok=False, output="url が空です。")

        # 検知回避: 直前アクセスから最小間隔を空ける
        interval = getattr(ctx.settings, "target_min_interval_sec", 0.0) if ctx.settings else 0.0
        last = ctx.scratch.get("_last_http", 0.0)
        now = time.monotonic()
        if interval and now - last < interval:
            time.sleep(interval - (now - last))
        ctx.scratch["_last_http"] = time.monotonic()

        try:
            resp = client.get(url)
        except httpx.HTTPError as e:
            return ToolResult(ok=False, output=f"取得失敗: {e}")

        keep = {"server", "location", "content-type"}
        headers = {k: v for k, v in resp.headers.items() if k.lower() in keep}
        body = resp.text[:_MAX_BODY]
        out = f"HTTP {resp.status_code} {headers}\n{body}"
        return ToolResult(ok=resp.status_code < 500, output=out)

    return Tool(SPEC, _run)


# 既定インスタンス（実ネットワーク用）
TOOL = make_http_get_tool()
