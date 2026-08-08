"""エントリポイント。

  （引数なし / 実行時）: OPENAI_BASE_URL・MCP_ENDPOINT・sidecar に接続して自走
  --demo  : モックで end-to-end（外部なし）
  --smoke : USER ID 出力 → チャレンジ一覧取得 → BONUS_FLAG があれば提出 の疎通確認
"""

from __future__ import annotations

import argparse
import logging
import sys

from halctf.config import load_settings
from halctf.runtime import announce_user_id


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def run_demo() -> int:
    """モック標的+モックモデルで 1 問を自力で解けることを確認する。"""
    from examples.mock_target import MockTarget
    from halctf.client.mock import MockClient
    from halctf.loop.react import ReactAgent
    from halctf.services.base import Challenge
    from halctf.services.mock import MockPlatform
    from halctf.tools import default_registry
    from halctf.tools.base import ToolContext

    settings = load_settings()
    target = MockTarget()
    platform = MockPlatform(
        challenges=[Challenge(id="demo-web", name="demo", category="web", points=100)],
        accepted={"demo-web": target.flag},
    )
    ctx = ToolContext(
        target=target, submitter=platform, settings=settings, challenge_id="demo-web"
    )
    agent = ReactAgent(MockClient(), default_registry(), ctx, max_steps=settings.max_steps)
    result = agent.solve("この標的のフラグを取得して提出せよ")

    print("=" * 48)
    print(f"solved : {result.solved}")
    print(f"flag   : {result.flag}")
    print(f"steps  : {result.steps}")
    print(f"reason : {result.reason}")
    print("=" * 48)
    return 0 if result.solved else 1


def run_smoke() -> int:
    """提出パイプラインの疎通確認（実サービスに接続）。"""
    from halctf.runtime import log_identity_env
    from halctf.services.mcp import McpChallengeService
    from halctf.services.sidecar import SidecarClient

    settings = load_settings()
    announce_user_id(settings.user_id)
    log_identity_env()  # HAL_*/USER* のキー一覧を出す（uid キー名の特定用）
    mcp = McpChallengeService(settings.mcp_endpoint)
    sidecar = SidecarClient(settings.sidecar_url)
    try:
        challenges = mcp.list_challenges()
        print(f"[smoke] challenges: {[c.id for c in challenges]}", flush=True)
        if settings.bonus_flag:
            bonus = next(
                (c for c in challenges if "bonus" in (c.name + c.category + c.id).lower()),
                None,
            )
            if bonus:
                ok, msg = sidecar.submit(bonus.id, settings.bonus_flag)
                print(f"[smoke] bonus submit -> {ok} ({msg})", flush=True)
            else:
                print("[smoke] bonus 対応チャレンジ不明。提出はスキップ。", flush=True)
    finally:
        sidecar.done()
    return 0


def run_real() -> int:
    """実サービスに接続して自走する。"""
    from halctf.client.openai_compat import OpenAICompatClient
    from halctf.runner import AgentRunner
    from halctf.services.mcp import McpChallengeService
    from halctf.services.sidecar import SidecarClient

    settings = load_settings()
    client = OpenAICompatClient(
        base_url=settings.openai_base_url,
        models=settings.models,
        pinned_model=settings.agent_model,  # HAL_AGENT_MODEL があれば優先
        timeout_sec=settings.step_timeout_sec,
    )
    mcp = McpChallengeService(settings.mcp_endpoint, timeout_sec=15.0)
    sidecar = SidecarClient(settings.sidecar_url)
    runner = AgentRunner(client, mcp, sidecar, settings)
    outcomes = runner.run()

    solved = [o for o in outcomes if o.solved]
    print(f"solved {len(solved)}/{len(outcomes)}: {[o.challenge_id for o in solved]}", flush=True)
    # 正常完了は必ず exit 0。非ゼロだとプラットフォームがクラッシュ扱いで
    # 再実行し、得点済みでも run が FAILED になる（得点は /submit で別途記録済み）。
    return 0


def main() -> int:
    _configure_logging()
    parser = argparse.ArgumentParser(prog="halctf", description="HalCTF autonomous agent")
    parser.add_argument("--demo", action="store_true", help="モックで end-to-end")
    parser.add_argument("--smoke", action="store_true", help="提出パイプラインの疎通確認")
    args = parser.parse_args()

    settings = load_settings()
    if args.demo or settings.use_mock:
        return run_demo()
    if args.smoke:
        return run_smoke()
    return run_real()


if __name__ == "__main__":
    raise SystemExit(main())
