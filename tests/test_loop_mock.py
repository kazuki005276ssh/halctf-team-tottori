"""結合テスト: モックモデル + モック標的で 1 問を自力で解けること。

フェーズ1 のゴール（動くエージェントが 1 問を自力で解く）の自動検証。
"""

from examples.mock_target import MockTarget
from halctf.client.mock import MockClient
from halctf.loop.react import ReactAgent
from halctf.services.base import Challenge
from halctf.services.mock import MockPlatform
from halctf.tools import default_registry
from halctf.tools.base import ToolContext


def _agent():
    target = MockTarget()
    platform = MockPlatform(
        challenges=[Challenge(id="demo-web", name="demo", category="web")],
        accepted={"demo-web": target.flag},
    )
    ctx = ToolContext(
        target=target, submitter=platform, settings=None, challenge_id="demo-web"
    )
    return ReactAgent(MockClient(), default_registry(), ctx, max_steps=10), platform, target


def test_agent_solves_mock_challenge():
    agent, platform, target = _agent()
    result = agent.solve("フラグを取得して提出せよ")
    assert result.solved
    assert result.flag == target.flag
    assert result.reason == "solved"
    assert platform.completed  # done() が呼ばれ run を締めている


def test_agent_recon_before_exploit_reasonable_steps():
    agent, _, _ = _agent()
    result = agent.solve("フラグを取得して提出せよ")
    assert result.steps <= 5
