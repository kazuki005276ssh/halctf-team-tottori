"""環境変数駆動の設定。

HalCTF プラットフォームは実行時（detonation）に以下を**注入する**。我々は読むだけ:
  - OPENAI_BASE_URL : OpenAI 互換の推論エンドポイント（sidecar が中継）
  - MCP_ENDPOINT    : チャレンジ探索 / フラグ提出の MCP サーバ
  - HAL_*           : 実行アイデンティティ（USER ID など）
  - BONUS_FLAG      : 提出パイプラインのスモークテスト用フラグ
sidecar は 127.0.0.1:9000 で全てを中継する（/submit・/done もここ）。

ローカル検証用に、同名の HALCTF_ 付き変数でも上書きできるようにしてある
（実行時は無印の OPENAI_BASE_URL 等が最優先）。
"""

from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HALCTF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),  # model_* フィールド名の警告を抑止
    )

    # --- プラットフォーム注入（無印が最優先、ローカルは HALCTF_ で上書き可）---
    openai_base_url: str = Field(
        "http://127.0.0.1:9000/llm",
        validation_alias=AliasChoices("OPENAI_BASE_URL", "HALCTF_OPENAI_BASE_URL"),
    )
    mcp_endpoint: str = Field(
        "http://127.0.0.1:9000/mcp",
        validation_alias=AliasChoices("MCP_ENDPOINT", "HALCTF_MCP_ENDPOINT"),
    )
    sidecar_url: str = Field(
        "http://127.0.0.1:9000",
        validation_alias=AliasChoices("HAL_SIDECAR_URL", "HALCTF_SIDECAR_URL"),
    )
    # 起動 30 秒以内に `USER ID: <uid>` を stdout 出力する必要がある。
    # uid は HAL_* として注入される想定。正確なキー名は現地で要確認。
    user_id: str = Field(
        "unknown-uid",
        validation_alias=AliasChoices(
            "HAL_USER_ID", "HAL_UID", "HAL_USERID", "USER_ID", "HALCTF_USER_ID"
        ),
    )
    bonus_flag: str | None = Field(
        None, validation_alias=AliasChoices("BONUS_FLAG", "HALCTF_BONUS_FLAG")
    )

    # --- 実行時にプラットフォームが渡すチャレンジ情報（env-first。MCP 探索より優先）---
    # 各 run は 1 チャレンジにスコープされ、これらが注入される。
    hal_challenge_id: str | None = Field(None, validation_alias=AliasChoices("HAL_CHALLENGE_ID"))
    hal_challenge_name: str | None = Field(
        None, validation_alias=AliasChoices("HAL_CHALLENGE_NAME")
    )
    hal_challenge_category: str | None = Field(
        None, validation_alias=AliasChoices("HAL_CHALLENGE_CATEGORY")
    )
    hal_challenge_description: str | None = Field(
        None, validation_alias=AliasChoices("HAL_CHALLENGE_DESCRIPTION")
    )
    hal_challenge_slug: str | None = Field(
        None, validation_alias=AliasChoices("HAL_CHALLENGE_SLUG")
    )
    # 使用モデルもプラットフォームが指定する（あれば /models 検出より優先）
    agent_model: str | None = Field(None, validation_alias=AliasChoices("HAL_AGENT_MODEL"))

    # --- モデル（提供モデルは CTF ごとに異なる。優先順＝小型→大型で並べる）---
    # 起動時に GET {OPENAI_BASE_URL}/models で実際に使えるものを自動検出し、
    # このチェーンのうち利用可能な先頭を選ぶ（提供一覧が違っても不一致にならない）。
    model_chain: str = "llama-3.1-8b,qwen3.6-35b-a3b,google/gemma-4-26b-a4b-it-maas,llama3-2"

    # --- フラグ形式（正規表現。web スクレイプ時の抽出/自動提出用）---
    # 形式は問題ごとに違う: flag{...}（Bonus）や HALCTF{...}（Cassandra）等。
    # 「英字始まりの短い接頭辞 + { 記号無しの英数字列 }」に一般化しつつ、
    # CSS/JS の {...} を拾わないよう中身は英数字系のみ・6文字以上に限定。
    flag_regex: str = r"[A-Za-z][A-Za-z0-9_]{1,14}\{[A-Za-z0-9_+/=.\-]{6,256}\}"

    # --- ループ / 実行制御 ---
    max_steps: int = 40  # 多段(SQLi列挙/IAM role連鎖/SSRF経路探索)に届くよう余裕を持たせる
    dry_run: bool = Field(False, validation_alias=AliasChoices("HAL_DRY_RUN"))
    step_timeout_sec: int = 90
    run_budget_sec: int = 3300  # 実行上限 1h に対し余裕を見る
    heartbeat_sec: int = 45  # stdout 無音 2m でハングとみなされるため定期出力

    # --- 検知回避（"CAUGHT BY SOC" 対策）---
    # 1 チャレンジあたりの誤提出許容回数。超えたら深追いせず切り上げる。
    max_flag_attempts: int = 3
    # 標的への連続アクセス間隔（秒）。総当たり的な挙動を避ける。
    target_min_interval_sec: float = 0.4

    # --- ローカル検証: mock で外部なしに end-to-end を回す ---
    use_mock: bool = False

    @property
    def models(self) -> list[str]:
        return [m.strip() for m in self.model_chain.split(",") if m.strip()]


def load_settings() -> Settings:
    return Settings()
