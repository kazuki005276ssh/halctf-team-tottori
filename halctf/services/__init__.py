"""services 層: HalCTF プラットフォームとの接点。

  - ChallengeService : MCP 経由のチャレンジ探索 / ヒント
  - Submitter        : フラグ提出 (POST /submit) と完了通知 (POST /done)

実行時は sidecar (127.0.0.1:9000) と MCP_ENDPOINT を叩く実装、
ローカル検証時は MockPlatform を使う。ループ層はこれらのインターフェースにのみ依存する。
"""

from halctf.services.base import Challenge, ChallengeService, Submitter
from halctf.services.mcp import McpChallengeService
from halctf.services.mock import MockPlatform
from halctf.services.sidecar import SidecarClient

__all__ = [
    "Challenge",
    "ChallengeService",
    "Submitter",
    "McpChallengeService",
    "SidecarClient",
    "MockPlatform",
]
