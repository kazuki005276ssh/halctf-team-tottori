"""結合テスト: runner が探索→攻略→完了通知まで自走すること（env フラグ問題）。"""

from halctf.client.mock import MockClient
from halctf.config import Settings
from halctf.runner import AgentRunner
from halctf.services.base import Challenge
from halctf.services.mock import MockPlatform
from halctf.tools import web_registry


def test_runner_solves_env_flag_challenge(monkeypatch):
    monkeypatch.setenv("FLAG_1", "flag{mock_starter}")
    settings = Settings(_env_file=None, heartbeat_sec=999)
    platform = MockPlatform(
        challenges=[Challenge(
            id="starter-1", name="Warm-up", category="Misc",
            description="フラグは環境変数 FLAG_1 にある。", points=50,
        )],
        accepted={"starter-1": "flag{mock_starter}"},
    )
    runner = AgentRunner(
        MockClient(), platform, platform, settings, registry=web_registry()
    )
    outcomes = runner.run()

    assert len(outcomes) == 1
    assert outcomes[0].solved
    assert outcomes[0].challenge_id == "starter-1"
    assert platform.completed  # done() が最後に呼ばれている
    assert ("starter-1", "flag{mock_starter}") in platform.submitted
