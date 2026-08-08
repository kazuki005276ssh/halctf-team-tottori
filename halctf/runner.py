"""AgentRunner: 1 run のオーケストレーション。

  起動(USER ID) → heartbeat → チャレンジ探索 → 各チャレンジを ReAct で攻略 → 完了通知(done)

検知回避（"CAUGHT BY SOC" 対策）の方針:
  - 易しい確実な問題から順に、静かに取る（総当たりしない）
  - 誤提出は上限で打ち切る（flag_submit ツール側で制御）
  - 解決済みはスキップ、残り予算を見て切り上げる
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from halctf.client.base import LLMClient
from halctf.loop.react import ReactAgent
from halctf.runtime import Heartbeat, announce_user_id, log_identity_env
from halctf.services.base import Challenge, ChallengeService, Submitter
from halctf.tools import ToolContext, web_registry
from halctf.tools.base import ToolRegistry

logger = logging.getLogger("halctf.runner")

TASK_TEMPLATE = """次の CTF チャレンジのフラグを取得して提出してください。

{brief}

方針:
- 環境変数にフラグがある場合は read_env で読む。
- web 標的なら http_get で偵察・攻略する（robots.txt も確認）。
- 確信の持てるフラグが得られたら flag_submit で提出する。誤提出は避ける。"""


@dataclass
class ChallengeOutcome:
    challenge_id: str
    solved: bool
    flag: str | None
    steps: int
    reason: str


class AgentRunner:
    def __init__(
        self,
        client: LLMClient,
        challenges: ChallengeService,
        submitter: Submitter,
        settings,
        *,
        registry: ToolRegistry | None = None,
        target=None,
    ) -> None:
        self.client = client
        self.challenges = challenges
        self.submitter = submitter
        self.settings = settings
        self.registry = registry or web_registry()
        self.target = target

    def solve_challenge(self, ch: Challenge, *, deadline: float) -> ChallengeOutcome:
        ctx = ToolContext(
            target=self.target,
            submitter=self.submitter,
            settings=self.settings,
            challenge_id=ch.id,
        )
        agent = ReactAgent(
            client=self.client,
            registry=self.registry,
            ctx=ctx,
            max_steps=self.settings.max_steps,
            run_budget_sec=self.settings.run_budget_sec,
        )
        agent.emit_completion = False  # run 全体の完了通知は runner が最後に出す
        task = TASK_TEMPLATE.format(brief=ch.brief())
        result = agent.solve(task, deadline=deadline)
        logger.info(
            "challenge %s: solved=%s reason=%s", ch.id, result.solved, result.reason
        )
        return ChallengeOutcome(ch.id, result.solved, result.flag, result.steps, result.reason)

    def run(self, *, max_challenges: int | None = None) -> list[ChallengeOutcome]:
        announce_user_id(self.settings.user_id)
        log_identity_env()  # uid の正確な env キー名を初回ログで特定するため
        deadline = time.monotonic() + self.settings.run_budget_sec
        outcomes: list[ChallengeOutcome] = []

        with Heartbeat(self.settings.heartbeat_sec):
            try:
                challenges = self.challenges.list_challenges()
            except Exception as e:  # 探索失敗でも done は出す
                logger.error("チャレンジ探索に失敗: %s", e)
                challenges = []

            # 未解決を、確実に取れる易しい順（点数昇順）に。検知回避で堅実に積む。
            todo = [c for c in challenges if not c.solved]
            todo.sort(key=lambda c: (c.points if c.points is not None else 0))
            logger.info("探索: 全 %d 問 / 未解決 %d 問", len(challenges), len(todo))

            for i, ch in enumerate(todo):
                if max_challenges is not None and i >= max_challenges:
                    break
                if time.monotonic() > deadline:
                    logger.info("予算超過につき打ち切り")
                    break
                # 詳細（説明・標的URL）を取得してから挑む
                try:
                    detail = self.challenges.get_challenge(ch.id)
                except Exception as e:
                    logger.warning("get_challenge 失敗 %s: %s", ch.id, e)
                    detail = ch
                outcomes.append(self.solve_challenge(detail, deadline=deadline))

            self.submitter.done()
        return outcomes
