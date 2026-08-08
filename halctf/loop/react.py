"""ReAct 系の自律決定ループ。

観測 → 思考 → ツール選択 → 実行 → 観測 を繰り返す。
小型モデル向けの工夫:
  - システムプロンプトは短く構造化
  - 状態を外部保持し、毎ターン全履歴を渡さない（state.build_messages）
  - 同一手の繰り返しを検出して打ち切る（ループ検出）
  - フラグ受理 or 手数上限 or 予算超過で完了通知を出して締める
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass

from halctf.client.base import ChatMessage, LLMClient
from halctf.loop.state import RunState
from halctf.tools.base import ToolContext, ToolRegistry

logger = logging.getLogger("halctf.loop")

SYSTEM_PROMPT = """あなたは CTF の自律ペンテストエージェントです。
目的: 標的を偵察し、脆弱性を突いてフラグ (flag{...}) を取得し、提出することです。
方針:
- 手順は「偵察(recon) → 攻略(exploit) → フラグ提出(flag_submit)」が基本。
- 必ず提供されたツールを使って行動する。推測だけで終わらせない。
- フラグ文字列が得られたら直ちに flag_submit を呼ぶ。
- 同じ手を繰り返さない。効かない手は変える。
簡潔に判断し、無駄な手数を避けること。"""


@dataclass
class RunResult:
    solved: bool
    flag: str | None
    steps: int
    reason: str  # "solved" | "max_steps" | "budget" | "stuck" | "loop_detected"


def _signature(name: str, args: dict) -> str:
    return f"{name}:{json.dumps(args, sort_keys=True, ensure_ascii=False)}"


class ReactAgent:
    def __init__(
        self,
        client: LLMClient,
        registry: ToolRegistry,
        ctx: ToolContext,
        *,
        max_steps: int = 20,
        run_budget_sec: int = 900,
        loop_repeat_threshold: int = 3,
    ) -> None:
        self.client = client
        self.registry = registry
        self.ctx = ctx
        self.max_steps = max_steps
        self.run_budget_sec = run_budget_sec
        self.loop_repeat_threshold = loop_repeat_threshold
        # 単体利用時は run 終了で完了通知を出す。runner 配下では runner が最後に出す。
        self.emit_completion = True

    def solve(self, task_prompt: str, *, deadline: float | None = None) -> RunResult:
        state = RunState(system_prompt=SYSTEM_PROMPT, task_prompt=task_prompt)
        if deadline is None:
            deadline = time.monotonic() + self.run_budget_sec
        specs = self.registry.specs()

        while state.step < self.max_steps:
            if time.monotonic() > deadline:
                return self._finish(RunResult(False, None, state.step, "budget"))
            state.step += 1

            result = self.client.chat(state.build_messages(), tools=specs)
            assistant_msg = ChatMessage(
                role="assistant", content=result.content, tool_calls=result.tool_calls
            )
            state.add(assistant_msg)

            if not result.tool_calls:
                # ツールを呼ばずテキストだけ → 手詰まりとみなす。
                return self._finish(RunResult(False, state.flag, state.step, "stuck"))

            for tc in result.tool_calls:
                sig = _signature(tc.name, tc.arguments)
                state.action_signatures.append(sig)
                # ループ検出: 直近が同一手で埋まっていたら打ち切る。
                recent = state.recent_signatures(self.loop_repeat_threshold)
                if len(recent) >= self.loop_repeat_threshold and len(set(recent)) == 1:
                    logger.info("ループ検出: %s", sig)
                    return self._finish(
                        RunResult(False, state.flag, state.step, "loop_detected")
                    )

                tool = self.registry.get(tc.name)
                if tool is None:
                    obs = f"未知のツール: {tc.name}"
                    tres = None
                else:
                    tres = tool.run(tc.arguments, self.ctx)
                    obs = tres.output

                state.add(
                    ChatMessage(role="tool", content=obs, tool_call_id=tc.id, name=tc.name)
                )

                if tres and tres.flag_captured:
                    state.flag = tres.flag_captured
                if tres and tres.done:
                    return self._finish(RunResult(True, state.flag, state.step, "solved"))

        return self._finish(RunResult(False, state.flag, state.step, "max_steps"))

    def _finish(self, result: RunResult) -> RunResult:
        # completion signal を出して run を締める（単体利用時のみ）。
        submitter = self.ctx.submitter
        if self.emit_completion and submitter is not None and hasattr(submitter, "done"):
            try:
                submitter.done()
            except Exception as e:  # 完了通知失敗で結果は変えない
                logger.warning("完了通知に失敗: %s", e)
        logger.info(
            "run 終了: solved=%s reason=%s steps=%d flag=%s",
            result.solved,
            result.reason,
            result.steps,
            result.flag,
        )
        return result
