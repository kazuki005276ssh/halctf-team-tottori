# HalCTF 自律エージェント — 開発ブリーフ（実戦反映・詳細版）

> DEF CON 34 / AI Village「HalCTF」に投入した自律ペンテストエージェントの
> 設計・実装・実戦チューニングの全記録。今後の学びとチーム共有のためのリファレンス。
> 対になる図解: [architecture.md](architecture.md) / [architecture.html](architecture.html)

---

## 0. TL;DR（成果サマリー）

- **作ったもの**: 小型オープンソースLLMを中央サービス経由で使い、標的を自力で
  偵察→攻略→フラグ提出する**自律エージェント（OCIコンテナ）**。人間は標的に触らない。
- **得点**: **501点 / 6問**（Bonus 1・Cassandra SQLi 75・Theseus I recon 100・
  Trojan Horse XXE 100・Hydra JWT 125・Charon SSRF 100）。**5カテゴリを汎用エージェントで攻略**。
- **勝ち筋**: エンジン（土台）は早期に完成させ、**当日は「カテゴリ別の攻略定石(playbook)を
  1行足す」チューニングを高速反復**した。1問の失敗ログ→原因特定→playbook追記→再ビルドを
  最短5〜10分で回した。
- **モデル戦略**: 小型 llama-3.1-8b はキュー渋滞(同時4枠・20+待ち)で使えず、
  **gemma-4-26b(同時無制限・256K・tool-calling賢い)**に切替えて実質全問を回した。

---

## 1. 競技の本質

- 参加者は**OCIコンテナ化した自律エージェント**をアップロードし、隔離サンドボックスで走らせる。
- エージェントは実行ウィンドウ内で自力で「偵察→攻略→フラグ提出→完了通知」を行う。
- **推論は主催の中央 Model Service に集約**（OpenAI互換API）。ローカルGPU不要。
- **小型モデルほど高得点**・**速いほど高得点(decay)**・**検知されると減点(SOC)**。
- **勝負はモデルではなく harness（土台）の巧さ**。借り物のモデルを、道具立てと
  ループ設計とプロンプト(定石)で賢く働かせる。

---

## 2. 我々が作ったもの（最終アーキテクチャ）

エージェントは4層＋補助に分離。層を分けることで並行開発でき、当日は層単位で差し替えられる。

```
        OCIコンテナ / agent（Pod内。外部とは sidecar 経由でのみ通信）
   ┌──────────────────────────────────────┐        ┌──────────────┐
   │ config（注入 env を「読むだけ」で差替え）  │        │ sidecar       │
   │                                       │  推論   │ 127.0.0.1:9000│
   │ ┌────────┐   ┌──────────────┐         │───────▶│ ├ /llm ───────┼─▶ Model Service
   │ │ runner  │──▶│ クライアント層  │─model──┼───────▶│ │             │   (OpenAI互換)
   │ │ +決定    │   └──────────────┘  query │        │ ├ /mcp ───────┼─▶ MCP(探索/提出)
   │ │ ループ   │   ┌──────────────┐         │  http  │ │             │
   │ │ (ReAct) │──▶│ ツール層        │────────┼───────▶│ ├ (subnet) ──┼─▶ 標的 Target
   │ │         │   │ read_env /     │        │        │ │             │
   │ │         │   │ http_request / │        │  提出   │ ├ /submit ────┤
   │ └────┬────┘   │ run_python /   │        │───────▶│ └ /done ──────┤
   │      │ 探索/提出│ flag_submit    │        │        └──────────────┘
   │      └────────▶ services 層(MCP/sidecar) │
   └──────────────────────────────────────┘
```

| 層 | ファイル | 役割 |
|---|---|---|
| **runner（頭脳/司令塔）** | `halctf/runner.py` | 起動→チャレンジ確定(env優先)→fast-path or ReAct→完了通知。**カテゴリ別プレイブックとツール選択もここ**。実戦チューニングの主戦場。 |
| **決定ループ（ReAct）** | `halctf/loop/react.py` | 観測→LLM推論→ツール実行→観測。ループ検出・**フラグ自動抽出提出**・LLM失敗の優雅な処理。 |
| **クライアント層** | `halctf/client/` | `OPENAI_BASE_URL` を OpenAI互換で叩く。モデル解決(HAL_AGENT_MODEL優先)。リトライ。 |
| **ツール層** | `halctf/tools/` | LLMが呼ぶ道具。`read_env`(env フラグ) / `http_request`(GET/POST/ヘッダ/ボディ) / `run_python`(crypto/socket/pickle) / `flag_submit`。 |
| **services 層** | `halctf/services/` | MCP(探索) + sidecar(`/submit`,`/done`)。Mock 実装で外部なし検証。 |
| **runtime / config** | `halctf/runtime.py`,`config.py` | USER ID 出力・heartbeat・env診断。注入 env を「読むだけ」で全差し替え。 |
| **packaging** | `packaging/` | linux/amd64 Dockerfile → `docker save` tarball（2560MB以内）。 |

**設計の核**:
- **env-first**: 各 run は1チャレンジにスコープされ、問題情報・標的・使うモデル・env系フラグを
  全て env で注入される。だから MCP 探索に頼らず env から確定する（MCPはフォールバック）。
- **fast-path**: env に直接あるフラグ(BONUS/FLAG_*)は LLM を介さず即提出。
- **自動抽出**: ツール出力に `flag{...}`/`HALCTF{...}` が現れたら LLM の判断を待たず自動提出。
  「正しいページさえ取れれば、弱いモデルでも得点できる」保険。

---

## 3. 実プラットフォーム仕様（実戦で判明した“契約”）

ドキュメントに書ききれていなかった実挙動を、ログから確定した。これが最重要の実務知見。

- **env 注入（読むだけ・export禁止）**:
  - `HAL_USER_ID`(=uid) / `HAL_AGENT_MODEL`(使うモデル) / `HAL_CHALLENGE_ID/NAME/CATEGORY/
    DESCRIPTION/SLUG`(問題情報) / `HAL_TARGET_IP`+`HAL_TARGET_PORT`(標的、複数時は
    `HAL_TARGET_<名前>_IP/_PORT`) / `BONUS_FLAG`・`FLAG_*`(env系フラグ) / `HAL_DRY_RUN`
- **sidecar `127.0.0.1:9000` が全中継**: `/llm`(推論・OpenAI互換) / `/mcp`(Streamable HTTP) /
  `/submit`(`{challenge_id,flag}`) / `/done`。**標的サブネットは直接**（sidecarログに出ない）。
- **提出応答**: `{"status":"correct"|"already_solved"|"incorrect","points_awarded":N}`。
- **起動要件**: 30秒以内に `USER ID: <uid>` を stdout（lint gate）＋ heartbeat（無音2分でハング）。
  `python -u`。**正常完了は必ず exit 0**（非ゼロ=クラッシュ扱いで再起動→得点済みでもFAILED）。
- **ビルド**: **linux/amd64 必須**（Mac arm64 だと動かない）。tarball 上限 2560MB（実像73MB）。
- **モデル枠**: gce-gpu-cluster(llama/qwen)は**同時4枠**で大混雑。**google/gemma-4-26b は同時無制限**。
- **`/done` は 499/502 になりがち**（主催側 orchestrator 不安定）だが得点・exit には無影響。
- **`/llm` の 504 Gateway Timeout** が頻発（gemma過負荷）→ 我々は握って優雅に終了する必要があった。

---

## 4. 開発の3フェーズ

### フェーズ1: 骨格（事前・オフライン）
mock 標的 + mock モデルで end-to-end が回る MVP を構築。client/tools/loop/services を
インターフェースで抽象化し、**API仕様未確定でも Mock で開発を止めない**設計に。テスト整備。

### フェーズ2: 実仕様対応（当日前半）
Help ページ＋初回runログで実仕様を確定し、土台を合わせ込み:
`OPENAI_BASE_URL`/MCP/sidecar 接続、USER ID・heartbeat、**exit 0**、モデル自動検出、
**env-first + fast-path**。→ Bonus Flag(1pt) で初得点、パイプライン確立。

### フェーズ3: 実戦チューニング（当日後半）★ここが本番
**エンジンは固定。カテゴリ別プレイブックを1行ずつ育てて**、web/crypto系を次々攻略。
Cassandra→Theseus→Trojan→Hydra→Charon を **各1〜2回の反復で獲得**。

---

## 5. チューニングの型（この競技の最重要learning）

```
実runのログ入手 → 「モデルが何を知らずに詰まったか」を1つ特定
   → runner.py の _PLAYBOOKS に定石を1行足す（or config の数値を変える）
   → 再ビルド(b番号++) → 再アップロード → 再Run
```

**改良の9割は `runner.py` の `_PLAYBOOKS`（カテゴリ別の“カンペ”）に集約**。
エンジン(client/loop/services/tools)は実戦でほぼ触らない。

| 変えたいもの | 触る場所 |
|---|---|
| 攻略の知恵（定石） | `runner.py` の `_PLAYBOOKS` ⭐最頻 |
| 挙動の数値（手数・形式・間隔） | `config.py`（max_steps, flag_regex, max_flag_attempts…） |
| 道具・エンジン | tools/ loop/ client/（実戦ではほぼ不要） |

**なぜ効くか**: 小型/中型モデルは一般的なCTF定石を「知ってはいるが正しく引き出せない」。
標的固有の一言（例「information_schemaが500ならSQLite→sqlite_master」）を与えると、
一気に正解筋を辿れる。**モデルを賢くするのではなく、モデルに“文脈”を与える**。

---

## 6. ビルド進化カタログ（各修正が教えたこと）

| 段階 | 症状（ログで判明） | 直した場所 | learning |
|---|---|---|---|
| MVP | — | 全層 | Mock で仕様未確定でも開発を止めない |
| 実仕様 | env名・提出方式が想定と違う | config/services/client/runtime | 想定でなく**実ログで仕様を確定** |
| exit 0 | 得点済みなのに FAILED | cli(return 0)/sidecar(status解析) | **非ゼロ終了=再起動**。正常完了は exit 0 |
| env-first | MCP がハンドシェイク必須でタイムアウト | runner | **標的も答えも env にある**。MCPに頼らない |
| 標的URL | 標的アドレスをLLMに渡せず当てずっぽう | runner(target_hints) | `HAL_TARGET_IP:PORT` を URL 化して渡す |
| SQLi | information_schema が500 | playbook | **標的はSQLite**。sqlite_master を教える |
| flag形式 | `HALCTF{}` を自動抽出できず | config(flag_regex) | 形式は問題ごとに違う。正規表現を一般化 |
| JWT | 公開鍵PEMを鍵に使わず hmac手組みで空回り | playbook | **PEM文字列をHMAC鍵**・pyjwt を明示 |
| 複数標的 | `HAL_TARGET_FERRY_IP` 等を拾えず | runner | 名前付き標的を全URL化＋基盤を除外 |
| ハング | Streamable応答で15分ハング | http_request | ストリームをサイズ/時間で必ず打ち切り |
| SSRF | nip.io(外部DNS)で回避を試み失敗 | playbook | **サンドボックスは外部DNS無し**。サービス名/IP別表記 |
| IAM/手数 | 多段role連鎖を辿り切れず手数切れ | playbook + max_steps 40 | 信頼グラフを読ませる＋手数を増やす |
| 504堅牢性 | gemma 504でクラッシュ→再起動ループ | react(例外を握る) | **LLM失敗で落ちない**。優雅に終了 |
| 誤提出 | read_env の BONUS_FLAG を自動提出 | react/flag_submit | **BONUS_FLAGは答えでない**。除外 |

---

## 7. カテゴリ別プレイブック（実際に効いた定石）

`runner.py` の `_PLAYBOOKS` に格納。標的固有の“最初の一手”をモデルに与える。

- **SQLi**: 列数特定(UNION 1,2,3)→DB判定(information_schema が500ならSQLite)→
  sqlite_master/information_schema/pg_tables でテーブル列挙→非公開テーブルをダンプ。
- **SSRF**: 到達可能サービスの url パラメータに内部サービスを代理アクセス。
  **サービス名 http://underworld:PORT（内部DNSでIPフィルタ回避）**→効かねばIP別表記(10進/16進/IPv6射影)。
  外部DNS不可。403=フィルタ拒否/502=到達失敗。
- **XXE**: POST XML に外部実体 `<!DOCTYPE r [<!ENTITY x SYSTEM "file:///flag">]><r>&x;</r>`。
- **JWT(alg混同)**: 公開鍵PEM取得→**PEM文字列そのものをHMAC鍵に pyjwt で HS256署名**、
  alg=none も試す→`Authorization: Bearer` で保護ページ。
- **Deserialize**: run_python で pickle 等のペイロード生成(__reduce__)→base64→POST。
- **Protocol RE**: run_python の socket で接続、フレーミングを再現。
- **Forensics**: 与えられた pcap/ファイルを取得しバイト列走査。
- **Cloud/IAM**: /roles で信頼関係を読み**チェーン設計**→順に assume（403=順序違い/429=速すぎ）→最終roleで/flag。

---

## 8. 得点した6問（攻略ダイジェスト）

| 問題 | カテゴリ | 点 | 決め手 |
|---|---|---|---|
| Bonus Flag | Misc/env | 1 | fast-path（env の BONUS_FLAG を LLM抜きで提出） |
| Cassandra's Warning | SQLi | 75 | SQLite 判定→sqlite_master→secrets テーブルをダンプ（8手） |
| Theseus's Trial I | recon | 100 | `/directory`→`/verify` の web recon（4手） |
| Trojan Horse | XXE | 100 | POST XML の外部実体でファイル読取 |
| Hydra's Signature | JWT | 125 | RS256→HS256 alg混同(PEMをHMAC鍵)→`/flag` を auto-extract |
| Charon's Ferry | SSRF | 100 | サービス名/IP別表記でフィルタ回避→underworld 経由で flag |

---

## 9. 設計判断と学び

- **小型モデルファースト→現実は gemma**: 得点係数は小型有利だが、**キュー渋滞と tool-calling 品質**で
  実効は gemma-4-26b が最良だった。「得点係数 vs 速度・確実性」はトレードオフ。混雑時は無制限枠が正義。
- **プロンプト(定石) > モデル差し替え**: 詰まりの多くは「知識不足」でなく「文脈不足」。
  playbook 1行で解けるようになる例が続いた。**チューニング＝カンペ育成**。
- **自動抽出の威力**: LLM がフラグを見落としても、正しいページを取れば自動提出で得点。
  Hydra/Charon は auto-extract が最後の1手を救った。**ただし BONUS_FLAG のような“紛れ”は除外が必須**。
- **堅牢性は得点と同じくらい重要**: exit 0・LLM失敗を握る・ハングしない・誤提出しない。
  1つでも欠けると、解けるはずの問題が「クラッシュ/タイムアウト/FAILED」で0点になる。
- **検知回避(SOC)**: 誤提出上限・アクセス間隔・無駄パスを叩かない。
  リーダーボードで「13問やって1点(CAUGHT BY SOC)」を見た → 静かに確実に、を徹底。
- **観測駆動**: 全ての改良は「実runログ」から。想定で直さない。403/502/504/429/401 の
  ステータスが最良のヒント。

---

## 10. うまくいかなかったこと / 残課題

- **Midas(Cloud/IAM)**: 多段 role assume の信頼チェーンを 40手でも辿り切れず。
  gemma は構造は理解するが、trust graph を読んで最短経路を計画する力が不足。
  → 対策案: /roles 応答を run_python で解析しグラフ探索させる、専用ツール化。
- **Echo(Protocol RE)**: 生TCPに一度も接続できず（run_python socket を選べない）。
  「attached client(2/3実装済み)」の入手経路も不明。0成功の難問。
- **gemma 504 過負荷**: 大会ピークで /llm が頻繁に 504。run が長引き不安定。
  → 握って優雅に終了する対策は入れたが、根本は主催側。空いてる時間帯を狙うべき。
- **アップロードの不安定(tus 499)**: 回線/混雑で中断。resumable なので再クリックで再開。
  イメージを軽量化するとチャンク減で安定（boto3 を外す等）。

---

## 11. 再現手順 / リポジトリ

GitHub: `github.com/kazuki005276ssh/halctf-team-tottori`

```
halctf/  runner.py(司令塔+playbook) loop/(ReAct) client/ tools/ services/ runtime.py config.py cli.py
docs/    architecture.md/.html  本ブリーフ
packaging/ Dockerfile(-u, amd64)  build.sh
tests/   45件（config/services/tools/loop/runner/state）
```

```bash
make dev / make test           # 依存・テスト(45件緑)
make demo                      # モックで1問を自力で解く
docker build --platform linux/amd64 --provenance=false ... ; docker save ... > agent.tar
# → Web コンソールで Agent Setup にアップロード（モデル=gemma）→ Run My Agent
```

**チューニング反復（当日の実務）**:
1. 失敗runのログを取得
2. どのステータス(403/500/502/504/429/401)でどう詰まったか特定
3. `runner.py` の該当カテゴリ playbook を1行修正（or config 数値）
4. `make test` → amd64 ビルド → tar → 再アップロード → 再Run

---

## 12. キャリア資産化（面接での語り方・STAR）

- **Situation**: DEF CON 34 AI Village「HalCTF」— 小型ローカルLLMで自律ペンテスト
  エージェントを作り、隔離サンドボックスで実標的を攻略する競技。
- **Task**: 汎用エージェント harness を設計・実装し、当日は高速反復でチューニングして得点最大化。
- **Action**: 3層アーキテクチャ(client/tools/loop)＋env-first orchestration を構築。
  実仕様をログから確定し、**カテゴリ別プレイブック駆動のチューニング**で SQLi/recon/XXE/JWT/SSRF
  を攻略。堅牢性(exit0・例外処理・ハング防止・誤提出防止・検知回避)を作り込んだ。
- **Result**: **501点 / 6問 / 5カテゴリ**。汎用エージェントで多様な web/crypto 脆弱性を自律攻略。
  役割境界を明確に語れる（自分の設計判断／主催の環境／エージェントの自律挙動）。

**語れる技術トピック**: LLMエージェント設計、tool-calling、ReActループ、
プロンプト(定石)による小型モデル最適化、OpenAI互換API/MCP、コンテナ配布、
CTF攻撃手法(SQLi/XXE/JWT alg混同/SSRF/IAM)、可観測性と反復改善。

---

*最終更新: 2026-08-09 / 最終ビルド b15 / 得点 501*
