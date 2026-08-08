"""run_python ツール: python3 コードを実行する。

http_request だけでは無理な領域を stdlib で賄う:
  - JWT alg 混同: base64 + hmac/hashlib（公開鍵を HS256 の鍵に流用 / alg=none）
  - 安全でないデシリアライズ: pickle ペイロード生成
  - 生 TCP バイナリプロトコル(Echo): socket
  - 任意の計算・変換・ファイル操作

シェルのエスケープが要らないぶん小型モデルにも書きやすい。検知回避のため
タイムアウトと出力上限を設ける。標的サブネットには到達可能（socket/urllib可）。
"""

from __future__ import annotations

import subprocess
from typing import Any

from halctf.client.base import ToolSpec
from halctf.tools.base import Tool, ToolContext, ToolResult

SPEC = ToolSpec(
    name="run_python",
    description=(
        "python3 のコードを実行し stdout/stderr を得る。"
        "暗号(hmac/hashlib/base64 で JWT 偽造)、pickle 生成、socket での生TCP、"
        "urllib での HTTP など、http_request で無理なことに使う。"
        "結果は print で出力すること。標的サブネットには到達できる。"
    ),
    parameters={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "実行する python3 コード。"},
        },
        "required": ["code"],
    },
)

_MAX_OUT = 8000


def make_run_python_tool(*, timeout: int = 30) -> Tool:
    def _run(args: dict[str, Any], ctx: ToolContext) -> ToolResult:
        code = args.get("code") or ""
        if not code.strip():
            return ToolResult(ok=False, output="code が空です。")
        to = getattr(ctx.settings, "step_timeout_sec", timeout) if ctx.settings else timeout
        try:
            proc = subprocess.run(
                ["python3", "-c", code],
                capture_output=True,
                text=True,
                timeout=min(int(to), 120),
            )
        except subprocess.TimeoutExpired:
            return ToolResult(ok=False, output=f"タイムアウト（{timeout}s）")
        out = ((proc.stdout or "") + (proc.stderr or ""))[:_MAX_OUT]
        return ToolResult(ok=proc.returncode == 0, output=out or "(出力なし)")

    return Tool(SPEC, _run)


TOOL = make_run_python_tool()
