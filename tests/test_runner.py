"""結合テスト: runner の env-first フロー（fast-path と ReAct フォールバック）。"""

from halctf.client.mock import MockClient
from halctf.config import Settings
from halctf.runner import AgentRunner, challenge_from_env, obvious_env_flag
from halctf.services.base import Challenge
from halctf.services.mock import MockPlatform
from halctf.tools import web_registry


def _settings(**env):
    return Settings(_env_file=None, heartbeat_sec=999, **env)


def test_challenge_from_env(monkeypatch):
    monkeypatch.setenv("HAL_CHALLENGE_ID", "1")
    monkeypatch.setenv("HAL_CHALLENGE_NAME", "Bonus Flag")
    monkeypatch.setenv("HAL_CHALLENGE_CATEGORY", "Bonus")
    s = Settings(_env_file=None)
    ch = challenge_from_env(s)
    assert ch and ch.id == "1" and ch.category == "Bonus"


def test_obvious_env_flag_bonus(monkeypatch):
    monkeypatch.setenv("BONUS_FLAG", "flag{bonus_here}")
    ch = Challenge(id="1", category="Bonus", extra={"slug": "bonus"})
    assert obvious_env_flag(ch) == "flag{bonus_here}"


def test_obvious_env_flag_by_description(monkeypatch):
    monkeypatch.setenv("FLAG_1", "flag{env_one}")
    ch = Challenge(id="1", category="Misc", description="read FLAG_1 and submit")
    assert obvious_env_flag(ch) == "flag{env_one}"


def test_runner_fast_path_submits_bonus_without_llm(monkeypatch):
    # BONUS_FLAG が env にあり、challenge も env 注入 → LLM を介さず即提出で解ける
    monkeypatch.setenv("BONUS_FLAG", "flag{bonus_here}")
    monkeypatch.setenv("HAL_CHALLENGE_ID", "1")
    monkeypatch.setenv("HAL_CHALLENGE_NAME", "Bonus Flag")
    monkeypatch.setenv("HAL_CHALLENGE_CATEGORY", "Bonus")
    monkeypatch.setenv("HAL_CHALLENGE_SLUG", "bonus")
    settings = Settings(_env_file=None, heartbeat_sec=999)

    platform = MockPlatform(challenges=[], accepted={"1": "flag{bonus_here}"})
    runner = AgentRunner(MockClient(), platform, platform, settings, registry=web_registry())
    outcomes = runner.run()

    assert len(outcomes) == 1
    assert outcomes[0].solved and outcomes[0].reason == "fast-path"
    assert outcomes[0].steps == 0  # LLM を1回も呼んでいない
    assert ("1", "flag{bonus_here}") in platform.submitted
    assert platform.completed


def test_runner_react_fallback_when_no_env_flag(monkeypatch):
    # env フラグが無い web 系 → ReAct にフォールバック（MockClient が read_env で解く）
    monkeypatch.setenv("FLAG_1", "flag{via_react}")
    monkeypatch.setenv("HAL_CHALLENGE_ID", "webish")
    monkeypatch.setenv("HAL_CHALLENGE_NAME", "Env reader")
    monkeypatch.setenv("HAL_CHALLENGE_CATEGORY", "Misc")
    monkeypatch.setenv("HAL_CHALLENGE_DESCRIPTION", "look at FLAG_1 in the environment")
    settings = Settings(_env_file=None, heartbeat_sec=999)

    # obvious_env_flag は description の FLAG_1 を拾うので、まず fast-path で解ける想定
    platform = MockPlatform(challenges=[], accepted={"webish": "flag{via_react}"})
    runner = AgentRunner(MockClient(), platform, platform, settings, registry=web_registry())
    outcomes = runner.run()
    assert outcomes[0].solved


def test_target_hints_combines_ip_port(monkeypatch):
    monkeypatch.setenv("HAL_TARGET_IP", "10.244.0.103")
    monkeypatch.setenv("HAL_TARGET_PORT", "9002")
    from halctf.runner import target_hints_from_env
    hints = target_hints_from_env()
    assert any("http://10.244.0.103:9002" in h for h in hints)


def test_target_hints_excludes_flags(monkeypatch):
    monkeypatch.setenv("FLAG_1", "flag{secret}")
    monkeypatch.setenv("BONUS_FLAG", "flag{bonus}")
    from halctf.runner import target_hints_from_env
    hints = target_hints_from_env()
    assert not any("flag{" in h for h in hints)


def test_target_hints_multi_service(monkeypatch):
    monkeypatch.setenv("HAL_TARGET_FERRY_IP", "10.244.0.17")
    monkeypatch.setenv("HAL_TARGET_FERRY_PORT", "9004")
    monkeypatch.setenv("HAL_TARGET_UNDERWORLD_IP", "10.244.0.15")
    monkeypatch.setenv("HAL_TARGET_UNDERWORLD_PORT", "9005")
    from halctf.runner import target_hints_from_env
    hints = target_hints_from_env()
    joined = " ".join(hints)
    assert "http://10.244.0.17:9004" in joined and "FERRY" in joined
    assert "http://10.244.0.15:9005" in joined and "UNDERWORLD" in joined


def test_target_hints_excludes_infra(monkeypatch):
    monkeypatch.setenv("HAL_TARGET_IP", "10.0.0.9")
    monkeypatch.setenv("HAL_TARGET_PORT", "8080")
    monkeypatch.setenv("MCP_ENDPOINT", "http://127.0.0.1:9000/mcp/")
    monkeypatch.setenv("OPENAI_BASE_URL", "http://127.0.0.1:9000/llm")
    from halctf.runner import target_hints_from_env
    hints = " ".join(target_hints_from_env())
    assert "10.0.0.9:8080" in hints
    assert "127.0.0.1:9000" not in hints  # 補助基盤は除外
