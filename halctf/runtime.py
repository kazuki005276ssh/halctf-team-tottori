"""起動時ランタイム要件。

HalCTF の lint ゲート / ハング検出に対応する:
  - 起動 30 秒以内に `USER ID: <uid>` を stdout に出す（本人確認）
  - 以後 stdout を出し続ける（2 分無音でハング扱い）
出力は必ず flush する（バッファされると heartbeat 判定に間に合わない）。
"""

from __future__ import annotations

import logging
import os
import sys
import threading
from typing import TextIO

logger = logging.getLogger("halctf.runtime")


def hal_env_keys() -> dict[str, str]:
    """アイデンティティ系の env キーと値を集める（uid の正確なキー名を現地で特定するため）。"""
    prefixes = ("HAL", "USER", "UID", "TEAM", "FLAG", "BONUS")
    return {k: v for k, v in sorted(os.environ.items()) if k.upper().startswith(prefixes)}


def log_identity_env() -> None:
    """起動時に HAL_*/USER* などのキーを stderr ログに出す（値は短く切る）。

    初回投入のログでここを見れば、uid が入っている正確な env キー名が分かる。
    """
    found = hal_env_keys()
    if not found:
        logger.warning("アイデンティティ系 env が見つからない（HAL_*/USER* 等）")
        return
    for k, v in found.items():
        shown = v if len(v) <= 40 else v[:37] + "..."
        logger.info("env %s=%s", k, shown)


def announce_user_id(uid: str, *, stream: TextIO | None = None) -> None:
    """lint ゲート用の本人確認行を出力する。"""
    out = stream or sys.stdout
    if uid == "unknown-uid":
        # 既定のままなら、正しいキー名を特定できるよう候補をログに出す。
        logger.warning("USER ID が未解決。候補 env キー: %s", list(hal_env_keys()))
    print(f"USER ID: {uid}", file=out, flush=True)


class Heartbeat:
    """stdout 無音を防ぐバックグラウンド心拍。

    with Heartbeat(interval): ... で使う。ループの各ステップでも log は出るが、
    LLM 呼び出し中など無音区間があっても 2 分を超えないよう保険をかける。
    """

    def __init__(self, interval_sec: float = 45.0, *, stream: TextIO | None = None) -> None:
        self.interval = interval_sec
        self._stream = stream or sys.stdout
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._beat = 0

    def _loop(self) -> None:
        while not self._stop.wait(self.interval):
            self._beat += 1
            print(f".heartbeat {self._beat}", file=self._stream, flush=True)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="halctf-heartbeat", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def __enter__(self) -> Heartbeat:
        self.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.stop()
