# HalCTF Agent — DEF CON 34 / AI Village 自律ペンテストエージェント

HalCTF（AI Village）向けの自律エージェント harness。オープンソースの小型
ローカルモデルを中央 Model Service（OpenAI 互換）経由で使い、標的を
**偵察 → 攻略 → フラグ提出**まで自走させる。詳細な競技仕様と戦略は
[HalCTF_開発ブリーフ.md](HalCTF_開発ブリーフ.md) を参照。

> **状態**: フェーズ1 MVP。モック標的 + モックモデルでローカル end-to-end が
> 通る。API 仕様は未確定なので env + インターフェースで抽象化済み。

## クイックスタート

```bash
make dev          # 開発依存を含めてインストール
make test         # ユニット + 結合テスト
make demo         # モックで 1 問を自力で解く（外部 API 不要）
```

`make demo` が `solved: True` を出せば、harness の骨格は生きている。

## アーキテクチャ（ブリーフ §3）

```
halctf/
  config.py         env 駆動の設定（API/モデル/フラグ形式を差し替え可能に）
  client/           中央 Model Service への OpenAI 互換クライアント
    base.py           共通型 + LLMClient インターフェース（抽象境界）
    openai_compat.py  実クライアント（/chat/completions・モデル多段）
    mock.py           外部 API 不要のモックモデル（定石ポリシー）
  tools/            エージェントの道具（小型モデル対策で 3 つに絞る）
    recon.py / exploit.py / flag_submit.py / shell.py(Phase2)
  loop/             ReAct 自律ループ
    react.py          観測→思考→ツール選択→実行→観測、ループ検出、完了通知
    state.py          外部状態 + コンテキスト圧縮（履歴を全部渡さない）
  submit/           フラグ提出 / 完了通知 API の抽象化（Http / Mock）
  cli.py            エントリポイント（--demo / 実 API）
spec/               API 仕様の置き場（未確定8項目・確定次第ここに）
packaging/          Dockerfile + build.sh（docker save → tarball, 2.5GB以内）
examples/           モック標的（ローカル検証用）
tests/              抽出 / ツール / 状態 / 結合の各テスト
```

## 設定

`.env.example` を `.env` にコピーして値を記入（`.env` はコミットしない）。
すべて `HALCTF_` プレフィックスの環境変数で、コード非依存に差し替えられる。

| 変数 | 意味 |
|---|---|
| `HALCTF_MODEL_BASE_URL` / `HALCTF_MODEL_API_KEY` | 中央 Model Service |
| `HALCTF_MODEL_CHAIN` | モデル多段（左が最優先の小型） |
| `HALCTF_SUBMIT_BASE_URL` / `_SUBMIT_PATH` / `_COMPLETION_PATH` | 提出・完了通知 |
| `HALCTF_FLAG_REGEX` | フラグ抽出の正規表現 |
| `HALCTF_MAX_STEPS` / `_RUN_BUDGET_SEC` | ループ手数・時間予算 |
| `HALCTF_USE_MOCK` | true でモック（外部 API 不要） |

## ビルド（OCI イメージ → tarball）

```bash
make build    # packaging/out/halctf-b{n}-{sha}.tar を出力（各 run ユニークタグ）
```

## 未確定事項（着手前に潰す）

API 仕様・サンドボックス制約・実行ウィンドウ長・フラグ形式などは
[spec/README.md](spec/README.md) に集約。Player Preview / Discord で確定させ、
`config.py` の既定値と `client`/`submit` のスキーマを揃える。

## 次にやること（フェーズ2）

- 実 API 結線（`spec/` 確定後）と実標的への接続（HTTP/shell ツール有効化）
- モデル多段の切替ロジック（小型で失敗 → 中型フォールバック、加点最適化）
- カテゴリ判定 → 定石初手の決め打ち（速度＝得点）
- ログ強化（当日の改善反復のための可観測性）
