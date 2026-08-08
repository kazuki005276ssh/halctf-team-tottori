"""ローカル検証用のモックプラットフォーム。

ChallengeService と Submitter の両方を満たし、外部サービスなしで
runner / loop を end-to-end で回せるようにする。
"""

from __future__ import annotations

from halctf.services.base import Challenge


class MockPlatform:
    def __init__(
        self,
        challenges: list[Challenge] | None = None,
        accepted: dict[str, str] | None = None,
    ) -> None:
        # 既定は STARTER 相当（env フラグ + 簡単な web）を模した1問
        self._challenges = challenges or [
            Challenge(
                id="starter-1",
                name="Warm-up (env flag)",
                category="Misc",
                description="フラグは環境変数 FLAG_1 に入っている。読み取って提出せよ。",
                points=50,
                attempts_remaining=5,
            )
        ]
        # challenge_id -> 正解フラグ
        self._accepted = accepted or {"starter-1": "flag{mock_starter}"}
        self.submitted: list[tuple[str, str]] = []
        self.completed = False

    # --- ChallengeService ---
    def list_challenges(self, ctf=None, category=None) -> list[Challenge]:
        return list(self._challenges)

    def get_challenge(self, challenge_id: str) -> Challenge:
        for c in self._challenges:
            if c.id == challenge_id:
                return c
        return Challenge(id=challenge_id)

    def get_challenge_status(self, challenge_id: str) -> Challenge:
        return self.get_challenge(challenge_id)

    def request_hint(self, challenge_id: str, index: int) -> str:
        return f"(mock hint {index} for {challenge_id})"

    # --- Submitter ---
    def submit(self, challenge_id: str, flag: str) -> tuple[bool, str]:
        self.submitted.append((challenge_id, flag))
        if self._accepted.get(challenge_id) == flag:
            for c in self._challenges:
                if c.id == challenge_id:
                    c.solved = True
            return True, "accepted"
        return False, "incorrect flag"

    def done(self) -> None:
        self.completed = True
