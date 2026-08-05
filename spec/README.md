# spec/ — HalCTF API 仕様の置き場

API 仕様が**未確定**なので、確定情報をここに集約する。コード側は
`halctf/config.py` の env とインターフェースで抽象化してあるので、
ここが埋まったら `client/openai_compat.py` と `submit/flag_api.py` の
パス・スキーマを微修正するだけで実結線できる。

## 埋めるべき項目（ブリーフ §2 の未確定8項目）

1. **model query** — 推論リクエストの正確なパス・スキーマ（OpenAI 互換のどこまで？）
2. **flag submission** — 提出のパス・リクエスト/レスポンス形式・受理判定フィールド
3. **completion signal** — 完了通知のパス・ペイロード
4. **モデル指定方法** — `model` パラメータ名・利用可能モデル名・小型モデル加点式
5. **フラグ形式** — 正規表現（`HALCTF_FLAG_REGEX` に反映）
6. **サンドボックス制約** — egress / 許可ツール / 実行時間上限 / 標的ネットワーク
7. **実行ウィンドウ長** — 1 run の分数（`HALCTF_RUN_BUDGET_SEC` に反映）
8. **各 run ユニークビルドの意味** — タグ違いで足りるか差分が要るか

## 入手元

- Player Preview: https://aivillage.org/halctf/player-preview/
- AI Village Discord: https://aivillage.org/discord/

## ファイル

- `halctf_api.example.md` — 確定前の仮スキーマ（実物入手後に差し替え）
