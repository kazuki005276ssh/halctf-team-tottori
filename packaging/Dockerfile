# HalCTF エージェント OCI イメージ。
# 制約: 2.5GB 以内。推論は中央サービスなのでモデル重みは同梱しない。
# 軽量ベース + 依存最小化でスリムに保つ。
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 依存だけ先に入れてレイヤキャッシュを効かせる。
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体。
COPY pyproject.toml README.md ./
COPY halctf ./halctf
COPY examples ./examples
RUN pip install --no-cache-dir --no-deps -e .

# 実行時アイデンティティ（OPENAI_BASE_URL / MCP_ENDPOINT / HAL_*）は
# detonation 時にプラットフォームが注入する。ここでは設定しない（読むだけ）。
# -u で stdout を無バッファ化（USER ID 出力・heartbeat をブロックさせない）。
ENTRYPOINT ["python3", "-u", "-m", "halctf.cli"]
