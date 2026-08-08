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
    # LLM の flag_submit か、exploit 出力からの auto-extract のどちらでも解ける
    assert result.reason in ("solved", "auto-solved")
    assert platform.completed  # done() が呼ばれ run を締めている


def test_agent_recon_before_exploit_reasonable_steps():
    agent, _, _ = _agent()
    result = agent.solve("フラグを取得して提出せよ")
    assert result.steps <= 5


def test_auto_submit_from_tool_output(monkeypatch):
    """ツール出力にフラグが現れたら、LLM が flag_submit を呼ばなくても自動提出して解ける。"""
    from halctf.client.base import ChatResult, ToolCall
    from halctf.config import Settings
    from halctf.loop.react import ReactAgent
    from halctf.services.mock import MockPlatform
    from halctf.tools import web_registry
    from halctf.tools.base import ToolContext

    # http_request を1回呼ぶだけで、その出力にフラグが載っているモッククライアント
    class OneShotClient:
        def chat(self, messages, *, tools=None, model=None, **kw):
            called = any(tc.name == "http_request" for m in messages for tc in m.tool_calls)
            if not called:
                return ChatResult(
                    content="fetch",
                    tool_calls=[ToolCall(id="c1", name="http_request",
                                         arguments={"url": "http://t/"})],
                )
            return ChatResult(content="done", tool_calls=[])

    # http_request をスタブして固定レスポンス（フラグ入り）を返す
    import httpx

    from halctf.tools.http_request import make_http_request_tool
    def handler(req):
        return httpx.Response(200, text="welcome flag{auto_win} bye")
    reg = web_registry()
    reg.register(make_http_request_tool(transport=httpx.MockTransport(handler)))

    platform = MockPlatform(challenges=[], accepted={"1": "flag{auto_win}"})
    ctx = ToolContext(submitter=platform, settings=Settings(_env_file=None), challenge_id="1")
    agent = ReactAgent(OneShotClient(), reg, ctx, max_steps=5)
    res = agent.solve("get the flag")
    assert res.solved and res.flag == "flag{auto_win}" and res.reason == "auto-solved"
    assert ("1", "flag{auto_win}") in platform.submitted


def test_playbook_for_category():
    from halctf.runner import playbook_for_category
    assert "UNION SELECT" in playbook_for_category("Web / SQL Injection")
    assert "hmac" in playbook_for_category("Web / Auth")
    assert "pickle" in playbook_for_category("Web / Insecure Deserialization")
    assert playbook_for_category("Unknown / Thing") == ""
