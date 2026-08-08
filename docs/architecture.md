# HalCTF Agent — アーキテクチャ & 設計（実仕様対応版）

> DEF CON 34 / AI Village · HalCTF 向け自律ペンテストエージェント harness の内部設計ドキュメント。
> 図解版: [architecture.html](architecture.html)
> 状態: **実プラットフォーム仕様に対応済み**（テスト27件緑 / モック end-to-end で solved）

前半（0〜1章）で**基礎概念をゼロから**説明し、後半（2章〜）でそれが
**このプロジェクトの具体的なコード・通信**にどう落ちているかを示す。
Help ページで確定した実仕様（`OPENAI_BASE_URL` / MCP / sidecar `127.0.0.1:9000` /
USER ID・heartbeat）を反映済み。

---

## 0. そもそも何をするのか

### 一文で

**「標的サーバを自分で攻略してフラグ（秘密の文字列）を盗むAIプログラム」を作る競技。**
人間は標的に触らない。作るのは攻略を自動でやる*エージェント*の方。

### 当日の流れ

1. エージェント一式を **Docker イメージ**にして主催にアップロード
2. 主催の隔離環境（サンドボックス）で**起動**。同じ Pod に **sidecar（NGINX）**が同居し、
   すべての通信を `127.0.0.1:9000` で中継する
3. エージェントは自力で **偵察 → 攻略 → フラグ発見**
4. `flag{…}` を **提出**（sidecar の `/submit` か MCP）＝ 得点
5. **完了通知**（`/done`）を出す。数分でスコアとログ
6. ログを見て改善 → 再ビルド → 再投入

### 勝ち筋（リーダーボードから）

- 上位は薄く、数問確実に解くだけでトップ10に入れる。
- **「CAUGHT BY SOC」= 検知されると大幅減点**（総当たり・騒がしい挙動は自滅）。
  → **静かに・最小手数で・確実に取る**agentが勝つ。マイナス点チームが多いのはこれが理由。
- 小型モデルほど高得点。速く解くほど高得点（decay）。

---

## 1. 前提となる用語（ゼロから）

各用語を「**一言 / なぜ必要 / このプロジェクトでは具体的に**」の3点で。

### 1.1 OCIコンテナ / Docker イメージ

- **一言**: アプリと必要物一式を丸ごと固めた「持ち運べる箱」。
- **なぜ**: 手元と主催サーバで寸分違わず同じに動かすため。
- **具体**: [packaging/Dockerfile](../packaging/Dockerfile) が `python:3.11-slim` に `halctf/` を入れ、
  `docker save` で `.tar` にして提出（上限 **2560MB**）。ベースイメージは自由。
  `ENTRYPOINT` は `python3 -u`（`-u`＝無バッファ。USER ID 出力と heartbeat をブロックさせない）。

### 1.2 sidecar（127.0.0.1:9000）と実行アイデンティティ

- **一言**: 自分の Pod に同居する**中継役（NGINX）**。agent は外部と直接話さず、全部これ経由。
- **なぜ**: ネットワークを隔離しつつ、推論・提出・アイデンティティ注入を一点で担うため。
- **具体**: 実行時（detonation）に **`OPENAI_BASE_URL` / `MCP_ENDPOINT` / `HAL_*`** が
  環境変数として**注入される**。我々は**読むだけ**（自分で `export` すると自分の agent を壊す）。
  フラグ提出 `POST /submit`、完了通知 `POST /done` もここ。

### 1.3 中央 Model Service / OpenAI互換API

- **一言**: 主催の「LLMに質問する窓口」。sidecar が `OPENAI_BASE_URL` で中継。
- **なぜ**: 全員共通窓口。手元にGPU・モデル不要。
- **具体**: [halctf/client/openai_compat.py](../halctf/client/openai_compat.py) が
  `POST {OPENAI_BASE_URL}/chat/completions` を叩く。`api_key="not-needed"`（sidecar が実キーを注入）。
  使えるモデル: `llama3-2` / `llama-3.1-8b` / `qwen3.6-35b-a3b`（gce-gpu-cluster・同時4枠）、
  `google/gemma-4-26b-a4b-it-maas`（256K・同時無制限）。

### 1.4 MCP（Model Context Protocol）サーバ

- **一言**: **チャレンジの情報とフラグ提出**を提供する窓口。`MCP_ENDPOINT` にある。
- **なぜ**: 「どんな問題があるか」「その説明」「提出」「ヒント」を得る標準インターフェース。
- **具体**: [halctf/services/mcp.py](../halctf/services/mcp.py) が JSON-RPC の `tools/call` を投げる。
  提供ツール: `list_challenges` / `get_challenge` / `get_challenge_status` /
  `submit_flag` / `request_hint` / `get_scoreboard` / `get_score_breakdown`。
  ※ フラグ提出は sidecar の `POST /submit` でも可（我々はこちらを既定に）。

### 1.5 LLMのツール呼び出し（tool-calling）

- **一言**: LLMに道具リストを渡すと、文章の代わりに「この道具をこの引数で呼んで」と返す仕組み。
- **なぜ**: LLMは自分でHTTPを送れない。実行するのはこちらのコード。
- **具体（実 CTF 用の道具）**: [halctf/tools/](../halctf/tools/) の `web_registry()`
  - `read_env` — 環境変数のフラグを読む（STARTER Flag 1: `FLAG_1`）
  - `http_get` — web 標的を GET（Flag 2: ページ、Flag 3: `robots.txt`）
  - `flag_submit` — 現在のチャレンジに提出（誤提出は上限で打ち切り＝検知回避）

### 1.6 エージェント / harness / 決定ループ（ReAct）

- **エージェント**: 目的を与えると自分で考え行動を繰り返すプログラム。**harness**＝その枠組み一式。
- **決定ループ / ReAct**: 「観察→考える→動く→また観察」を繰り返す。1回のLLM質問では足りないから*ループ*する。
- **具体**: [halctf/loop/react.py](../halctf/loop/react.py) の `while`。1周＝「LLMに1回聞く」＋「ツール1回実行」。

### 1.7 起動要件（USER ID / heartbeat）

- **USER ID**: 起動 **30秒以内**に `USER ID: <uid>` を stdout に出す（本人確認の lint ゲート）。
- **heartbeat**: stdout **無音2分でハング扱い**。定期出力し続ける。出力は必ず `flush`。
- **具体**: [halctf/runtime.py](../halctf/runtime.py) の `announce_user_id` と `Heartbeat`。

### 1.8 検知回避（"CAUGHT BY SOC"）

- **一言**: 標的への騒がしい挙動や総当たり提出は**検知され減点**される。
- **具体**: 誤提出は `max_flag_attempts`（既定3）で打ち切り、標的アクセスは `target_min_interval_sec`
  で間隔を空け、易しい確実な問題から静かに取る（[halctf/runner.py](../halctf/runner.py)）。

---

## 2. 全体像 — 層 + 外部境界（すべて sidecar 経由）

```
        OCIコンテナ / agent（Pod 内。外部とは sidecar 経由でのみ通信）
   ┌──────────────────────────────────────────┐         ┌───────────────┐
   │  config（OPENAI_BASE_URL / MCP_ENDPOINT /   │         │  sidecar       │
   │          HAL_* を「読むだけ」）              │         │ 127.0.0.1:9000 │
   │                                           │  推論    │  (NGINX 中継)   │
   │  ┌────────┐     ┌───────────────┐         │─────────▶│  ├─ /llm ───────┼──▶ Model Service
   │  │ 決定    │────▶│ クライアント層   │─model──┼─────────▶│  │              │    (OpenAI互換)
   │  │ ループ  │     └───────────────┘  query  │         │  ├─ /mcp ───────┼──▶ MCP サーバ
   │  │(ReAct) │     ┌───────────────┐         │  探索/   │  │              │    (challenge/提出)
   │  │        │────▶│ ツール層         │─http───┼─────────▶│  ├─ (subnet) ──┼──▶ 標的 Target
   │  │        │     │ read_env/http_  │  get   │         │  │              │
   │  │        │     │ get/flag_submit │        │  提出/   │  ├─ /submit ────┤
   │  └────┬───┘     └──────┬────────┘         │  完了    │  └─ /done ──────┤
   │       │  discover/submit│  (services層)     │─────────▶│                │
   │       └────────────────┘                  │         └───────────────┘
   └──────────────────────────────────────────┘
```

**agent は sidecar (127.0.0.1:9000) としか話さない。** sidecar が推論(`/llm`)・
チャレンジと提出(`/mcp`)・標的サブネット・`/submit`・`/done` を振り分ける。
外部依存はこの1点に集約され、すべて env で差し替え可能。

| 用途 | 我々のコード | 経路 |
|---|---|---|
| 推論（次の手を聞く） | `client/` | `OPENAI_BASE_URL` → sidecar `/llm` → Model Service |
| チャレンジ探索・ヒント | `services/mcp.py` | `MCP_ENDPOINT` → sidecar `/mcp` |
| 標的の偵察・攻略 | `tools/http_get.py` | 現 CTF のサブネット（sidecar 経由） |
| フラグ提出・完了 | `services/sidecar.py` | `POST /submit` / `POST /done` |

---

## 3. 各層の責務

| 層 | ディレクトリ | 責務 |
|---|---|---|
| クライアント層 | `halctf/client/` | `OPENAI_BASE_URL` に `chat/completions`。モデル多段。Mock あり。 |
| ツール層 | `halctf/tools/` | LLM が呼ぶ道具。実CTF用 `web_registry`（read_env/http_get/flag_submit）、デモ用 `default_registry`（recon/exploit/flag_submit）。 |
| 決定ループ層 | `halctf/loop/` | ReAct。状態外部保持・コンテキスト圧縮・ループ検出。 |
| services 層 | `halctf/services/` | プラットフォーム接点。`McpChallengeService`（探索）＋ `SidecarClient`（`/submit`,`/done`）＋ `MockPlatform`。 |
| ランタイム | `halctf/runtime.py` | USER ID 出力・heartbeat。 |
| ランナー | `halctf/runner.py` | 起動→探索→各チャレンジを ReAct→`done` のオーケストレーション。検知回避の方針もここ。 |
| 設定 | `halctf/config.py` | プラットフォーム注入 env（無印優先）＋ローカル上書き（HALCTF_）。 |
| パッケージング | `packaging/` | Dockerfile（`-u`）＋ tarball 化（2560MB 検査）。 |

---

## 4. 1 run の流れ（runner オーケストレーション）

```
起動: USER ID: <uid> を出力（30秒以内）
  │
  ├─ Heartbeat 開始（stdout 無音を防ぐ）
  │
  ├─ services.list_challenges()  … MCP で問題一覧を取得
  │      ↓ 未解決を「点数昇順（易しい確実な順）」に並べる  ← 検知回避で堅実に
  │
  ├─ 各チャレンジについて:
  │      services.get_challenge(id)  … 説明・標的URLを取得
  │      ReActループで攻略:
  │        観察→LLM推論→ツール実行→観察  ×N
  │        （read_env で env フラグ / http_get で web / flag_submit で提出）
  │        誤提出が上限に達したら深追いせず打ち切り  ← 検知回避
  │
  └─ services.done()  … 完了通知でキュー枠を解放
```

**STARTER の3問がそのまま通る設計**:
Flag 1（env の `FLAG_1`）→ `read_env`、Flag 2（ページ）→ `http_get`、
Flag 3（`robots.txt`）→ `http_get` で末尾を `/robots.txt`。

---

## 5. 決定ループ — ReAct と終了条件

1周＝「状態を組む→LLM推論→ツール実行→観測を状態へ」。終了条件:

- `flag 受理` → 解決 / `ツール無し` → 手詰まり / `同一手×3` → ループ検出 /
  `step上限・予算超過` → 打ち切り / `誤提出上限` → 打ち切り（検知回避）

小型モデル対策として履歴が伸びたら要約に畳み直近だけ渡す（`loop/state.py`）。
runner 配下では完了通知は runner が最後に1回だけ出す（`emit_completion=False`）。

---

## 6. 未確定を止めなかった抽象化（そして確定後の結線）

ループ・ツールは**インターフェースにのみ依存**し、実装が本物かモックかを知らない。
だから仕様確定前も `MockPlatform` で開発でき、**確定後は実装を差し込むだけ**だった。

```
        決定ループ / runner  ── インターフェースにのみ依存 ──┐
                                                          ▼
   ┌──────────────┐   ┌──────────────────┐   ┌──────────────────────────┐
   │ MockClient    │┈▶│ LLMClient         │◀┈│ OpenAICompatClient        │
   │ MockPlatform  │┈▶│ ChallengeService  │◀┈│ McpChallengeService       │
   │ (探索+提出)    │┈▶│ Submitter         │◀┈│ SidecarClient (/submit)   │
   └──────────────┘   └──────────────────┘   └──────────────────────────┘
      （ローカル検証）                            （実サービス／確定済み）
                       env で選択: HALCTF_USE_MOCK
```

MCP のワイヤ形式だけは現地で要確認だが、ズレても `services/mcp.py` の
`_call`/`_parse_result` を直すだけで済むよう1ファイルに閉じ込めてある。

---

## 7. リポジトリ構成

```
halctf/
├─ config.py           # プラットフォーム注入 env（無印優先）+ ローカル上書き
├─ runtime.py          # USER ID 出力 + heartbeat
├─ runner.py           # 起動→探索→各チャレンジ ReAct→done + 検知回避
├─ client/             # OPENAI_BASE_URL への口（base/openai_compat/mock）
├─ tools/              # read_env / http_get / flag_submit（実）, recon / exploit（デモ）
├─ loop/               # react.py（ReAct）+ state.py（圧縮）
├─ services/           # mcp.py（探索）+ sidecar.py（/submit,/done）+ mock.py + base.py
└─ cli.py              # --demo / --smoke / 実行
spec/                  # API 仕様メモ（実仕様で更新）
packaging/             # Dockerfile（-u）+ build.sh（tarball, 2560MB 検査）
examples/              # mock_target.py
tests/                 # config / services / tools / loop / runner / state（27件）
```

```bash
make dev      # 依存インストール
make test     # 27 件
make demo     # モックで 1 問を解く → solved: True
python3 -m halctf.cli --smoke   # 実サービスに対する提出パイプライン疎通確認
make build    # OCI イメージ → tarball
```

---

## 8. 現地での確認事項（実行前チェック）

実仕様は Help でほぼ確定したが、**現地でしか確認できない**残り:

1. **USER ID の正確な env キー名** — `HAL_*` のどれか。起動ログで `HAL_*` のキー一覧を確認し
   `config.py` の `user_id` alias を合わせる（現状 `HAL_USER_ID` 等を候補で読む）。
2. **MCP のワイヤ形式** — handshake の要否・`tools/call` の result スキーマ。`--smoke` で
   `list_challenges` が返るか確認。ズレたら `services/mcp.py` を調整。
3. **`/submit` のスキーマ** — `{challenge_id, flag}` で受理フィールドが `correct` か。`--smoke` で確認。
4. **BONUS_FLAG の対象チャレンジ** — どの challenge_id に出すか（`--smoke` はヒューリスティックで探す）。

---

## 付録. 実際の通信（Help より・確定）

```jsonc
// 推論（次の手を聞く）
POST {OPENAI_BASE_URL}/chat/completions      // api_key は "not-needed"
{ "model": "llama3-2", "messages": [...], "tools": [...] }

// フラグ提出（sidecar の簡易経路）
POST http://127.0.0.1:9000/submit
{ "challenge_id": "...", "flag": "flag{...}" }

// 完了通知（キュー枠を解放）
POST http://127.0.0.1:9000/done

// チャレンジ探索（MCP / JSON-RPC）
POST {MCP_ENDPOINT}
{ "jsonrpc":"2.0","id":1,"method":"tools/call",
  "params":{"name":"list_challenges","arguments":{}} }
```

**System Limits（Help）**: run 1h / heartbeat 無音 2m / tarball 2560MB /
mem 512Mi–2Gi / CPU 500m–2 / storage 4–8Gi / team 5 /
gce-gpu-cluster 同時4・google 同時無制限。
