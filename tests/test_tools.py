from examples.mock_target import MockTarget
from halctf.services.base import Challenge
from halctf.services.mock import MockPlatform
from halctf.tools import default_registry, web_registry
from halctf.tools.base import ToolContext


def _ctx(challenge_id="demo-web"):
    target = MockTarget()
    platform = MockPlatform(
        challenges=[Challenge(id="demo-web", name="demo", category="web")],
        accepted={"demo-web": target.flag},
    )
    return ToolContext(
        target=target, submitter=platform, settings=None, challenge_id=challenge_id
    )


def test_default_registry_has_three_tools():
    assert set(default_registry().names()) == {"recon", "exploit", "flag_submit"}


def test_web_registry_tools():
    assert set(web_registry().names()) == {"read_env", "http_request", "flag_submit"}


def test_http_request_get_and_post():
    import httpx

    from halctf.tools.http_request import make_http_request_tool

    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["body"] = request.content.decode()
        seen["auth"] = request.headers.get("authorization", "")
        return httpx.Response(200, text="OK body")

    tool = make_http_request_tool(transport=httpx.MockTransport(handler))
    ctx = _ctx()
    # GET（既定）
    r = tool.run({"url": "http://t/search?q=1"}, ctx)
    assert r.ok and "OK body" in r.output and seen["method"] == "GET"
    # POST + ヘッダ + ボディ
    r = tool.run(
        {"url": "http://t/import", "method": "POST", "body": "<xml/>",
         "headers": {"Authorization": "Bearer x"}},
        ctx,
    )
    assert seen["method"] == "POST" and seen["body"] == "<xml/>" and seen["auth"] == "Bearer x"


def test_recon_stores_scratch():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("recon").run({"target": "default"}, ctx)
    assert res.ok
    assert "recon" in ctx.scratch


def test_exploit_right_technique_returns_flag():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("exploit").run({"target": "default", "technique": "path-traversal"}, ctx)
    assert "flag{mock_target_pwned}" in res.output


def test_flag_submit_accepts_correct_with_challenge_id():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("flag_submit").run({"flag": "flag{mock_target_pwned}"}, ctx)
    assert res.ok and res.done and res.flag_captured == "flag{mock_target_pwned}"


def test_flag_submit_rejects_wrong():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("flag_submit").run({"flag": "flag{wrong}"}, ctx)
    assert not res.ok and not res.done


def test_flag_submit_stops_after_attempt_limit():
    reg, ctx = default_registry(), _ctx()
    ctx.flag_attempts = 3  # 上限到達済み（settings 既定は 3）
    res = reg.get("flag_submit").run({"flag": "flag{wrong}"}, ctx)
    assert res.done and not res.ok  # 総当たり回避で打ち切り


def test_read_env_reads_value(monkeypatch):
    monkeypatch.setenv("FLAG_1", "flag{env_value}")
    reg, ctx = web_registry(), _ctx()
    res = reg.get("read_env").run({"name": "FLAG_1"}, ctx)
    assert res.ok and res.output == "flag{env_value}"


def test_read_env_missing_hides_value(monkeypatch):
    monkeypatch.delenv("NOPE_FLAG", raising=False)
    reg, ctx = web_registry(), _ctx()
    res = reg.get("read_env").run({"name": "NOPE_FLAG"}, ctx)
    assert not res.ok
