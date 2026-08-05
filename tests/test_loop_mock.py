"""結合テスト: モックモデル + モック標的で 1 問を自力で解けること。

これがブリーフ フェーズ1 のゴール（動くエージェントが 1 問を自力で解く）の
自動検証。CI でここが緑なら harness の骨格は生きている。
"""

from examples.mock_target import MockTarget
from halctf.client.mock import MockClient
from halctf.loop.react import ReactAgent
from halctf.submit import MockSubmitter
from halctf.tools import default_registry
from halctf.tools.base import ToolContext


def _agent():
    target = MockTarget()
    submitter = MockSubmitter(accepted_flags={target.flag})
    ctx = ToolContext(target=target, submitter=submitter, settings=None)
    return (
        ReactAgent(MockClient(), default_registry(), ctx, max_steps=10),
        submitter,
        target,
    )


def test_agent_solves_mock_challenge():
    agent, submitter, target = _agent()
    result = agent.solve("フラグを取得して提出せよ")
    assert result.solved
    assert result.flag == target.flag
    assert result.reason == "solved"
    # 完了通知が出ている（run を締めている）
    assert submitter.completed


def test_agent_recon_before_exploit():
    """偵察 → 攻略 → 提出の順序を踏んでいる（手数が妥当）。"""
    agent, _, _ = _agent()
    result = agent.solve("フラグを取得して提出せよ")
    # recon(1) + exploit(1) + flag_submit(1) = 3 手前後で解けるはず
    assert result.steps <= 5
