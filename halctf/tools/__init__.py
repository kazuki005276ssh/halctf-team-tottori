"""ツール層: エージェントの道具と、その登録レジストリ。"""

from __future__ import annotations

from halctf.tools import exploit, flag_submit, http_request, read_env, recon, run_python
from halctf.tools.base import Tool, ToolContext, ToolRegistry, ToolResult


def default_registry() -> ToolRegistry:
    """モックデモ用の最小3ツール（recon / exploit / flag_submit）。"""
    reg = ToolRegistry()
    reg.register(recon.TOOL)
    reg.register(exploit.TOOL)
    reg.register(flag_submit.TOOL)
    return reg


def web_registry() -> ToolRegistry:
    """実 CTF 用（env フラグ + web スクレイプ）。

    read_env: 環境変数に埋め込まれたフラグ用（STARTER Flag 1）
    http_request: web 標的への汎用 HTTP（GET の SQLi〜POST の XXE/deser、ヘッダ）
    flag_submit: 提出
    小型モデル対策でツールは3つに絞る。
    """
    reg = ToolRegistry()
    reg.register(read_env.TOOL)
    reg.register(http_request.TOOL)
    reg.register(flag_submit.TOOL)
    return reg


def power_registry() -> ToolRegistry:
    """暗号・バイナリ・デシリアライズ等の難問用（web に run_python を追加）。

    read_env / http_request / run_python / flag_submit の4つ。
    JWT・pickle・生TCP・forensics などは run_python（stdlib）で攻略する。
    """
    reg = web_registry()
    reg.register(run_python.TOOL)
    return reg


def registry_for_category(category: str) -> ToolRegistry:
    """チャレンジのカテゴリで道具を出し分ける（小型モデルの選択負荷を下げる）。

    純 web（SQLi/SSRF/XXE）は http_request 中心の3ツール。
    Auth(JWT)/Deserialization/Network/Forensics/Cloud/Crypto/Multi-Stage は
    run_python を足した4ツール。
    """
    cat = (category or "").lower()
    web_only = ("sql" in cat or "ssrf" in cat or "xxe" in cat) and "auth" not in cat
    if web_only:
        return web_registry()
    if cat.startswith("web") and not any(
        k in cat for k in ("auth", "deser", "jwt", "serial")
    ):
        return web_registry()
    return power_registry()


__all__ = [
    "Tool",
    "ToolContext",
    "ToolRegistry",
    "ToolResult",
    "default_registry",
    "web_registry",
    "power_registry",
    "registry_for_category",
]
