from examples.mock_target import MockTarget
from halctf.submit import MockSubmitter
from halctf.tools import default_registry
from halctf.tools.base import ToolContext


def _ctx():
    target = MockTarget()
    return ToolContext(
        target=target,
        submitter=MockSubmitter(accepted_flags={target.flag}),
        settings=None,
    )


def test_registry_has_three_tools():
    reg = default_registry()
    assert set(reg.names()) == {"recon", "exploit", "flag_submit"}


def test_recon_stores_scratch():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("recon").run({"target": "default"}, ctx)
    assert res.ok
    assert "recon" in ctx.scratch


def test_exploit_wrong_technique_fails_to_flag():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("exploit").run({"target": "default", "technique": "sqli"}, ctx)
    assert "flag{" not in res.output


def test_exploit_right_technique_returns_flag():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("exploit").run(
        {"target": "default", "technique": "path-traversal"}, ctx
    )
    assert "flag{mock_target_pwned}" in res.output


def test_flag_submit_accepts_correct():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("flag_submit").run({"flag": "flag{mock_target_pwned}"}, ctx)
    assert res.ok and res.done and res.flag_captured == "flag{mock_target_pwned}"


def test_flag_submit_rejects_wrong():
    reg, ctx = default_registry(), _ctx()
    res = reg.get("flag_submit").run({"flag": "flag{wrong}"}, ctx)
    assert not res.ok and not res.done
