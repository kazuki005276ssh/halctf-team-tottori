"""ローカル検証用のモック標的。

「偵察すると攻略の手掛かりが出て、正しい手法で攻略するとフラグが返る」
という最小の CTF 問題を再現する。実標的ネットワークの代役。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MockTarget:
    flag: str = "flag{mock_target_pwned}"
    expected_technique: str = "path-traversal"

    def recon(self, target: str) -> str:
        return (
            "ポート 80/tcp open (http)。\n"
            "GET /  -> 200 'Welcome'\n"
            "GET /files?name=readme -> 200 (ファイル読み取り機能あり)\n"
            "所見: name パラメータにパストラバーサルの可能性。"
            " exploit で technique='path-traversal' を試すとよい。"
        )

    def exploit(self, target: str, technique: str, payload: str = "") -> str:
        if technique == self.expected_technique:
            return (
                "GET /files?name=../../flag.txt -> 200\n"
                f"本文: {self.flag}\n"
                "（フラグを取得。flag_submit で提出せよ）"
            )
        return f"technique='{technique}' は効果がなかった。別の手を試す必要がある。"
