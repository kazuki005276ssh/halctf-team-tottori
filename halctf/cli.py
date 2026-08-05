"""エントリポイント: 1 チャレンジをエージェントに自走させる。

  --demo : モック標的 + モックモデルで外部 API なしに end-to-end を回す
  （引数なし）: .env の設定で実 Model Service / 提出 API に接続して走る
"""

from __future__ import annotations

import argparse
import logging
import sys
import time

from halctf.config import load_settings
from halctf.loop.react import ReactAgent
from halctf.tools import default_registry
from halctf.tools.base import ToolContext

DEFAULT_TASK = (
    "この標的に含まれる脆弱性を突いてフラグを取得し、提出してください。"
    "まず recon で偵察し、所見に基づいて exploit を試し、flag_submit で提出します。"
)


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )


def run_demo() -> int:
    """モックで 1 問を自力で解けることを確認する。"""
    from examples.mock_target import MockTarget
    from halctf.client.mock import MockClient
    from halctf.submit import MockSubmitter

    settings = load_settings()
    target = MockTarget()
    submitter = MockSubmitter(accepted_flags={target.flag})
    ctx = ToolContext(target=target, submitter=submitter, settings=settings)

    agent = ReactAgent(
        client=MockClient(),
        registry=default_registry(),
        ctx=ctx,
        max_steps=settings.max_steps,
        run_budget_sec=settings.run_budget_sec,
    )
    result = agent.solve(DEFAULT_TASK, deadline=time.monotonic() + settings.run_budget_sec)

    print("=" * 48)
    print(f"solved : {result.solved}")
    print(f"flag   : {result.flag}")
    print(f"steps  : {result.steps}")
    print(f"reason : {result.reason}")
    print("=" * 48)
    return 0 if result.solved else 1


def run_real(task: str) -> int:
    """実 Model Service / 提出 API に接続して走る（標的接続は要拡張）。"""
    from halctf.client.openai_compat import OpenAICompatClient
    from halctf.submit import HttpSubmitter

    settings = load_settings()
    client = OpenAICompatClient(
        base_url=settings.model_base_url,
        api_key=settings.model_api_key,
        models=settings.models,
        timeout_sec=settings.step_timeout_sec,
    )
    submitter = HttpSubmitter(
        base_url=settings.submit_base_url,
        submit_path=settings.submit_path,
        completion_path=settings.completion_path,
        api_key=settings.model_api_key,
    )
    # NOTE: 実標的への接続（HTTP/シェル等）は API/サンドボックス仕様の確定後に
    # ToolContext.target とツール層へ差し込む。現状は提出経路のみ実結線。
    ctx = ToolContext(target=None, submitter=submitter, settings=settings)

    agent = ReactAgent(
        client=client,
        registry=default_registry(),
        ctx=ctx,
        max_steps=settings.max_steps,
        run_budget_sec=settings.run_budget_sec,
    )
    result = agent.solve(task)
    print(f"solved={result.solved} flag={result.flag} steps={result.steps} reason={result.reason}")
    return 0 if result.solved else 1


def main() -> int:
    _configure_logging()
    parser = argparse.ArgumentParser(prog="halctf", description="HalCTF autonomous agent")
    parser.add_argument("--demo", action="store_true", help="モック標的で end-to-end を回す")
    parser.add_argument("--task", default=DEFAULT_TASK, help="エージェントへのタスク指示")
    args = parser.parse_args()

    settings = load_settings()
    if args.demo or settings.use_mock:
        return run_demo()
    return run_real(args.task)


if __name__ == "__main__":
    raise SystemExit(main())
