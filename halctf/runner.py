"""AgentRunner: 1 run のオーケストレーション（env-first）。

実プラットフォームは各 run を 1 チャレンジにスコープし、問題情報・challenge_id・
（env系なら）フラグまで env で注入する（HAL_CHALLENGE_* / BONUS_FLAG / FLAG_*）。
そこで探索は env を最優先し、MCP はフォールバックに回す。

  起動(USER ID) → heartbeat → チャレンジ確定(env優先) →
  fast-path（env にフラグがあれば LLM 抜きで即提出）→ 無ければ ReAct → done

検知回避（"CAUGHT BY SOC"）: 誤提出は上限で打切り、静かに確実に。
"""

from __future__ import annotations

import logging
import os
import re
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

_ENV_FLAG_HINT = re.compile(r"\b(FLAG_[A-Z0-9_]+|BONUS_FLAG)\b")


@dataclass
class ChallengeOutcome:
    challenge_id: str
    solved: bool
    flag: str | None
    steps: int
    reason: str


def challenge_from_env(settings) -> Challenge | None:
    """HAL_CHALLENGE_* からチャレンジを組む（注入されていれば）。"""
    cid = getattr(settings, "hal_challenge_id", None)
    if not cid:
        return None
    return Challenge(
        id=str(cid),
        name=getattr(settings, "hal_challenge_name", "") or "",
        category=getattr(settings, "hal_challenge_category", "") or "",
        description=getattr(settings, "hal_challenge_description", "") or "",
        extra={"slug": getattr(settings, "hal_challenge_slug", "") or ""},
    )


def obvious_env_flag(ch: Challenge) -> str | None:
    """env に直接置かれたフラグを見つける（Bonus / FLAG_<id> / 説明中の変数名）。

    LLM を介さず確実・高速に取れる env 系チャレンジ用。見つからなければ None。
    """
    cat = (ch.category or "").lower()
    slug = str(ch.extra.get("slug", "")).lower()
    # Bonus チャレンジ → BONUS_FLAG
    bonus = os.environ.get("BONUS_FLAG")
    if bonus and ("bonus" in cat or "bonus" in slug):
        return bonus
    # FLAG_<challenge_id>
    v = os.environ.get(f"FLAG_{ch.id}")
    if v:
        return v
    # 説明文が具体的な env 変数名に言及していれば（例「read FLAG_1」）
    m = _ENV_FLAG_HINT.search(ch.description or "")
    if m:
        v = os.environ.get(m.group(1))
        if v:
            return v
    return None


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
        agent.emit_completion = False  # 完了通知は runner が最後にまとめて出す
        task = TASK_TEMPLATE.format(brief=ch.brief())
        result = agent.solve(task, deadline=deadline)
        logger.info("challenge %s: solved=%s reason=%s", ch.id, result.solved, result.reason)
        return ChallengeOutcome(ch.id, result.solved, result.flag, result.steps, result.reason)

    def _discover(self) -> list[Challenge]:
        """env 優先でチャレンジを確定。無ければ MCP にフォールバック。"""
        env_ch = challenge_from_env(self.settings)
        if env_ch is not None:
            logger.info("env からチャレンジ確定: id=%s name=%s", env_ch.id, env_ch.name)
            return [env_ch]
        try:
            chs = [c for c in self.challenges.list_challenges() if not c.solved]
        except Exception as e:
            logger.error("MCP チャレンジ探索に失敗: %s", e)
            return []
        chs.sort(key=lambda c: (c.points if c.points is not None else 0))
        return chs

    def run(self, *, max_challenges: int | None = None) -> list[ChallengeOutcome]:
        announce_user_id(self.settings.user_id)
        log_identity_env()  # uid/challenge/model の注入 env を初回ログで確認
        deadline = time.monotonic() + self.settings.run_budget_sec
        outcomes: list[ChallengeOutcome] = []

        with Heartbeat(self.settings.heartbeat_sec):
            todo = self._discover()
            logger.info("対象: %d 問", len(todo))

            for i, ch in enumerate(todo):
                if max_challenges is not None and i >= max_challenges:
                    break
                if time.monotonic() > deadline:
                    logger.info("予算超過につき打ち切り")
                    break

                # fast-path: env に直接あるフラグは LLM 抜きで即提出
                flag = obvious_env_flag(ch)
                if flag:
                    accepted, msg = self.submitter.submit(ch.id, flag)
                    logger.info("fast-path 提出 %s -> %s (%s)", ch.id, accepted, msg)
                    outcomes.append(
                        ChallengeOutcome(
                            ch.id, accepted, flag if accepted else None, 0,
                            "fast-path" if accepted else "fast-path-rejected",
                        )
                    )
                    continue

                # それ以外は ReAct（web など）
                outcomes.append(self.solve_challenge(ch, deadline=deadline))

            self.submitter.done()
        return outcomes
