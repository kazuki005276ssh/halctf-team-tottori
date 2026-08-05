"""環境変数駆動の設定。

設計原則（ブリーフ §6「環境非依存」）:
  API エンドポイント・使用モデル・フラグ形式はすべて env で差し替える。
  提出方法や環境が変わっても同じコードで動くようにする。
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="HALCTF_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- 中央 Model Service（OpenAI 互換）---
    model_base_url: str = "http://localhost:8000/v1"
    model_api_key: str = "changeme"
    # 小型優先 → 難所フォールバックの多段。左が最優先。
    model_chain: str = "Llama-3.2-3B,Qwen3.5-4B,gpt-oss-120b"

    # --- フラグ提出 / 完了通知 API（未確定。spec 確定後に差し替え）---
    submit_base_url: str = "http://localhost:8000"
    submit_path: str = "/submit"
    completion_path: str = "/complete"

    # --- フラグ形式（正規表現）---
    flag_regex: str = r"flag\{[^}]+\}"

    # --- ループ制御 ---
    max_steps: int = 20
    step_timeout_sec: int = 60
    run_budget_sec: int = 900

    # --- ローカル検証: mock で外部 API なしに end-to-end を回す ---
    use_mock: bool = False

    @property
    def models(self) -> list[str]:
        return [m.strip() for m in self.model_chain.split(",") if m.strip()]


def load_settings() -> Settings:
    return Settings()
