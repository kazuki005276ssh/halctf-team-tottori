# DEF CON 34 コンテスト参加計画

**開催**：2026年8月6日（木）〜8月9日（日）／ Las Vegas Convention Center
**参加費**：オンライン決済済み
**併催**：DEF CON Training Las Vegas（8月10〜11日）
**テーマ**：Agency（技術における自己決定）

**公式リンク**
- コンテスト一覧：https://www.defcon.org/html/defcon-34/dc-34-contests.html
- ヴィレッジ一覧：https://defcon.org/html/defcon-34/dc-34-villages.html
- 統合スケジュール「The One!」：https://defcon.outel.org/dcwp/dc34/
- 公式InfoBooth：https://info.defcon.org
- 公式アプリ：Hacker Tracker（iOS / Android）

**この計画の目的**
AIエージェントセキュリティ／LLMアプリケーションセキュリティの専門家として、Microsoft・Google Cloud・AWS のSecurity Engineer / Solution Architect 職に対して語れる「実績」を持ち帰る。参加数を最大化するのではなく、面接で語れる密度の高い成果に絞る。

---

## 1. 優先順位

| 優先度 | コンテスト | 主催 | 狙う成果 | リンク |
|---|---|---|---|---|
| **S** | HALctf | AI Village | 自作の自律ペンテストエージェントを構築・実戦投入した実績 | https://aivillage.org |
| **A** | Escalation Desk CTF | Call Center Village | 会話型AIエージェントへの prompt injection 実戦 | https://defcon.org/html/defcon-34/dc-34-villages.html |
| **A** | Bug Bounty Village CTF | Bug Bounty Village | API・ビジネスロジック・AIチャットボット攻略、実レポート提出 | https://www.defcon.org/html/defcon-34/dc-34-contests.html |
| **A** | DC's Next Top Threat Model | — | 脅威モデリング＝Security Architect の職能そのものを競う | https://threatmodel.us |
| **A** | Kubernetes CTF | Container Security | AIワークロード基盤の攻防（土曜のみ本戦） | https://containersecurityctf.com |
| **B** | Apex Park | Cloud Village | AWS/GCP/Azure 横断のクラウドセキュリティ（8/7〜8/8） | https://www.cloud-village.org/dc34 |
| **B** | OWASP Foundation CTF | OWASP | 「壊す」だけでなく修正PRを出す＝セキュア開発の証明 | https://www.defcon.org/html/defcon-34/dc-34-contests.html |
| **B** | Fix the Flag | AppSec Village | 脆弱性の修正・ハードニングで加点される wargame | https://defcon.org/html/defcon-34/dc-34-villages.html |
| **C** | AI Village Plays Pokemon / HSPACE: AI Battlegrounds | AI Village 他 | エージェント構築・プロンプト設計を軽く体験 | https://aivillage.org |
| **C** | Adversary Wars CTF / Blue Team Village CTF | Adversary Village / BTV | 余力がある場合のみ | https://www.defcon.org/html/defcon-34/dc-34-contests.html |

**方針**：S と A に体力を集中する。全部やろうとすると全部が浅くなる。C は A の隙間が空いた場合のみ。

---

## 2. すでに参加できないもの（記録用）

| コンテスト | 理由 |
|---|---|
| DEF CON CTF（Benevolent Bureau of Birds） | オンライン予選が5月22〜24日に終了済み。通過者のみ本戦参加 |
| Battle of the Bots: Vishing Edition | 事前の Call for AI Competitors で選抜済み |
| Social Engineering Community Vishing Competition | 同上（Call for Competitors 選抜制） |
| Hacker Jeopardy | 事前登録必須 |

※来年以降を狙う場合、DEF CON CTF 予選は例年5月、Call for Competitors 系は春先に募集開始。**2027年に向けては3〜5月にチェックすること。**

---

## 3. Phase 1：今週（〜7月30日）

### ① HALctf エージェント準備・提出【最優先】

**URL**：https://aivillage.org
**AI Village 概要**：https://defcon.org/html/defcon-34/dc-34-villages.html

AI Village のメイン競技。**オープンソースモデルを使って自分専用のペンテストエージェントを書き、ファインチューニングする**内容。膨大な計算負荷に対応するため、エージェントは GCP 上で安全に実行され、**参加者ごとに専用GPUが割り当てられる**。

**重要な確認事項**
公式ページ上、2つの参加形態が示唆されている。どちらが自分に該当するか **aivillage.org で必ず確認すること**。

1. **事前提出型**：オープンソースLLMで動く自己完結型 Docker イメージを、DEF CON の約1週間前（**7月30日前後**）までに提出
2. **現地構築型**：会場で専用GPUの割り当てを受け、その場でエージェントを書き・ファインチューニングする

→ 事前提出枠が存在する場合、**それが唯一の不可逆な締切**になる。現地構築型のみであれば締切リスクは無く、事前準備の質が成績を決める。

**最小構成の方針**
- ツール3点（recon / exploit試行 / フラグ提出）＋ エージェントループ で可
- oshikatu-ai のツール定義・ループ設計をそのまま流用できる
- 完成度より「動くものを期限内に用意する」ことを優先

**関連**：AI Village では Drop-In Workshops も開催。LLMの動作原理、エージェントのゼロからの構築、prompt injection、マルウェア検知モデルの操作などを扱い、ローカルクラスタ上で実行される。HALctf の前段として有用。

**キャリア上の価値**：成績が振るわなくても「DEF CON で自作の自律ペンテストエージェントを構築・実戦投入した」という事実自体が、AIエージェントセキュリティ職の面接で最も強い差別化要素になる。

**最小構成の方針**
- ツール3点（recon / exploit試行 / フラグ提出）＋ エージェントループ で可
- oshikatu-ai のツール定義・ループ設計をそのまま流用できる
- 提出後の改良は効かないため、完成度より「動くものを期限内に出す」ことを優先

**キャリア上の価値**：成績が振るわなくても「DEF CON の自律エージェントCTFに自作エージェントを投入した」という事実自体が、AIエージェントセキュリティ職の面接で最も強い差別化要素になる。

### ② オンライン事前サインアップ（各5分程度）

- [ ] **Kubernetes CTF** → https://containersecurityctf.com （土曜本戦の枠確保）
- [ ] **Crack Me If You Can** → https://contest-2026.korelogic.com （登録推奨。Street クラスで）
- [ ] **DC's Next Top Threat Model** → https://threatmodel.us （登録メールを現地で開ける状態にしておく）
- [ ] **Cloud Village CTF（Apex Park）** → https://www.cloud-village.org/dc34 （8/7〜8/8開催。チーム参加可、上位3チームに賞）
- [ ] **OWASP CTF** → GitHub アカウント確認、fork → patch → PR の流れを一度素振り

### ③ DEF CON 公式 Discord 参加

各コンテストのチャンネルに入る。**開催時刻の確定情報はここが最速。**
公式Discordへの導線：https://info.defcon.org

---

## 4. Phase 2：出発前（〜8月5日）

### 持ち物（無いと参加できないもの）

- [ ] Burp Suite / Caido / OWASP ZAP のいずれか（**Bug Bounty Village CTF 必須**）
- [ ] 有線イーサネットアダプタ（Capture The Packet、HackFortress）
- [ ] ノイズキャンセリング付きヘッドセット＋マイク（**Escalation Desk CTF 強く推奨**）
- [ ] ラップトップ、充電器、モバイルバッテリー、電源タップ
- [ ] メモ用具（Cryptid Hunt 等の物理系で有用）

### 技術の素振り（各1〜2時間で十分）

- [ ] **prompt injection の型**：system prompt 漏洩、role 混同、間接注入
      → Escalation Desk と Bug Bounty の両方で効く
- [ ] **OWASP LLM Top 10** の再確認（AI SecureOps 受講済みのため復習レベル）
- [ ] **Kubernetes 権限昇格系**：ServiceAccount token、hostPath、RBAC 誤設定

---

## 5. Phase 3：現地4日間のスケジュール

### 8/5（水）前日

- ラスベガス到着
- バッジ受取場所の確認（オンライン決済済み）
- **Trace Labs OSINT の無料チケットを OSINT4Good スペースで受け取る**
- 会場レイアウトの下見

### 8/6（木）Day 1 — 偵察と仕込み

初日は多くのコンテストが立ち上がりきっていない。無理に競技せず、翌日以降の効率を最大化する日と位置づける。

- Contest Area / AI Village / Cloud Village / Bug Bounty Village の物理的な位置を把握
- **HALctf の自エージェント稼働状況を確認**。AI Village 運営に挨拶しておくと後の動きが早い
- DC's Next Top Threat Model の設計資料が配布されていれば受け取る
- **夜：Discord で各コンテストの実開催時刻を突き合わせ、時間割を確定する**

### 8/7（金）Day 2 — AI攻撃の日

| 時間帯 | 内容 |
|---|---|
| 午前 | **Bug Bounty Village CTF**（ビジネスロジック・API・AIチャットボット） |
| 午後 | **Escalation Desk CTF**（会話型AIエージェント突破。prompt injection 実戦） |
| 12:00〜 | Kubernetes CTF **Learning CTF** 開始。土曜本戦の予行として1時間触る |
| 隙間 | **Apex Park（Cloud Village CTF）** — 2日間通しなので随時加点 |

### 8/8（土）Day 3 — 主戦場（最重要日）

| 時間帯 | 内容 |
|---|---|
| **10:30〜17:30** | **Kubernetes CTF 競技本戦**（この日のみ。最優先で確保） |
| 隙間 | **DC's Next Top Threat Model** 提出（設計は事前に読み込んでおく） |
| 夕方以降 | **OWASP Foundation CTF**（exploit ＋ 修正PR でフラグ加算） |
| 余力 | Apex Park の追い込み |

土曜は競合が集中する。**Kubernetes CTF を軸に据え、他を前後に寄せる**判断を推奨。

### 8/9（日）Day 4 — 回収と仕上げ

- 午前：Apex Park / OWASP CTF の未回収フラグを詰める（多くのCTFは日曜昼で終了）
- **HALctf の結果確認 ＋ AI Village 運営との会話** ← 必ず時間を確保する。
  自エージェントの挙動に対するフィードバックは、面接ネタとして最も価値が高い
- 余力で AI Village Plays Pokemon / HSPACE: AI Battlegrounds を体験
- 夕方：結果発表・Closing Ceremony

### 8/10〜11（月・火）

DEF CON Training（AI Agent Security Masterclass を受講する場合）。
**前日までに体力を残す設計が必要。** 日曜は無理をしない。

---

## 6. 申し込みステップ一覧

| # | 項目 | 期限 | リンク／方法 | 状態 |
|---|---|---|---|---|
| 1 | DEF CON 34 参加登録 | — | オンライン決済 | ✅ 完了 |
| 2 | **HALctf 参加形態の確認＋エージェント準備** | **〜7/30頃** | https://aivillage.org | ⬜ |
| 3 | Kubernetes CTF 登録 | 出発前 | https://containersecurityctf.com | ⬜ |
| 4 | Cloud Village CTF 登録 | 出発前 | https://www.cloud-village.org/dc34 | ⬜ |
| 5 | Crack Me If You Can 登録 | 出発前 | https://contest-2026.korelogic.com | ⬜ |
| 6 | DC's Next Top Threat Model 登録 | 出発前 | https://threatmodel.us | ⬜ |
| 7 | OWASP CTF 準備 | 出発前 | GitHub アカウント／Git ワークフロー確認 | ⬜ |
| 8 | DEF CON 公式 Discord 参加 | 出発前 | https://info.defcon.org | ⬜ |
| 9 | Hacker Tracker アプリ導入 | 出発前 | iOS / Android アプリストア | ⬜ |
| 10 | Trace Labs OSINT チケット受取 | 現地・競技開始前 | OSINT4Good コミュニティスペース | ⬜ |
| 11 | Bug Bounty / Escalation Desk / Fix the Flag | 現地・当日 | 事前登録不要。飛び込み参加 | — |

---

## 7. 注意点

**開催時刻の確定情報について**
公式ページに明確な時刻が記載されているのは **Kubernetes CTF（土 10:30〜17:30、Learning CTF は金12:00〜日12:00）** など一部のみ。他の多くは直前確定となる。

→ **DEF CON 公式アプリ（Hacker Tracker）と各村の Discord** で確定情報が出るため、**Day 1（8/6）の夜に時間割を一度上書きする前提**で組むこと。

**体力配分**
4日間の本編に加えて8/10〜11のトレーニングが続く。土曜（Day 3）がピークになるよう設計し、日曜は回収と会話に充てる。

---

## 8. 参加後にやること（面接資産化）

- HALctf のエージェント設計・稼働結果を STAR 形式で言語化
  （役割境界を明確に：自分の設計判断 / 運営の環境提供 / エージェントの自律挙動を混同しない）
- Kubernetes CTF・Apex Park で得た具体的な攻撃手法と、それに対する防御設計の対応表を作成
- OWASP CTF で提出した修正PR を GitHub に残す（「直せる」ことの可視的証拠）
- 誇張・脚色は一切しない。実際に達成した内容のみを記載する

---

---

## 9. リンク集

### DEF CON 公式
| 内容 | URL |
|---|---|
| コンテスト一覧（正式な一次情報源） | https://www.defcon.org/html/defcon-34/dc-34-contests.html |
| ヴィレッジ一覧 | https://defcon.org/html/defcon-34/dc-34-villages.html |
| InfoBooth（公式情報ノード・Discord導線） | https://info.defcon.org |
| Hacker Tracker | iOS / Android の公式スケジュールアプリ |

### スケジュール統合サイト（非公式・実用性が高い）
| 内容 | URL |
|---|---|
| The One! DEF CON 34（HTML/PDF/CSV/ICAL/Google Calendar で出力可能） | https://defcon.outel.org/dcwp/dc34/ |
| The One! ヴィレッジ一覧（各村の公式サイト・SNSリンク集約） | https://defcon.outel.org/dcwp/dc34/activities/villages-list/ |
| InfoSecMap DEF CON 34 | https://infosecmap.com/event/def-con-34/ |

※公式・非公式いずれも**直前まで内容が更新される**。DEF CON開始1〜2日前でもスケジュール変更が発生する前提で見ること。

### 個別コンテスト
| コンテスト | URL |
|---|---|
| AI Village（HALctf / Plays Pokemon / Drop-In Workshops） | https://aivillage.org |
| Cloud Village（Apex Park CTF・8/7〜8/8） | https://www.cloud-village.org/dc34 |
| Kubernetes CTF | https://containersecurityctf.com |
| DC's Next Top Threat Model | https://threatmodel.us |
| Crack Me If You Can 2026 | https://contest-2026.korelogic.com |

### DEF CON Training（8/10〜11）
| 内容 | URL |
|---|---|
| Training 一覧 | https://training.defcon.org/collections/def-con-training-las-vegas-2026 |
| AI Agent Security Masterclass（第一候補） | https://training.defcon.org/collections/def-con-training-las-vegas-2026/products/ai-agent-security-masterclass-attacking-and-defending-autonomous-ai-systems-abhay-bhargav-vishnu-prasad-dctlv2026 |
| Securing the Future: Kubernetes & Cloud-Native（第二候補） | https://training.defcon.org/collections/def-con-training-las-vegas-2026/products/securing-the-future-defending-kubernetes-cloud-native-infrastructure-in-the-age-of-ai-madhu-akula-dctlv2026 |
| Black Belt Pentesting（AI軸とは別枠） | https://training.defcon.org/collections/def-con-training-las-vegas-2026/products/black-belt-pentesting-bug-hunting-millionaire-mastering-web-attacks-with-full-stack-exploitation-100-hands-on-dawid-czagan-dctlv2026 |

---

*最終更新：2026年7月22日*
