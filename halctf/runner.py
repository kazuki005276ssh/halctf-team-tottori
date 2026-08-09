"""AgentRunner: 1 run のオーケストレーション（env-first）。

実プラットフォームは各 run を 1 チャレンジにスコープし、問題情報・challenge_id・
（env系なら）フラグまで env で注入する（HAL_CHALLENGE_* / BONUS_FLAG / FLAG_*）。
そこで探索は env を最優先し、MCP はフォールバックに回す。

  起動(USER ID) → heartbeat → チャレンジ確定(env優先) →
  fast-path（env にフラグがあれば LLM 抜きで即提出）→ 無ければ ReAct → done

検知回避（"CAUGHT BY SOC"）: 誤提出は上限で打切り、静かに確実に。
"""

from __future__ import annotations

import logging
import os
import re
import time
from dataclasses import dataclass

from halctf.client.base import LLMClient
from halctf.loop.react import ReactAgent
from halctf.runtime import Heartbeat, announce_user_id, log_identity_env
from halctf.services.base import Challenge, ChallengeService, Submitter
from halctf.tools import ToolContext, registry_for_category
from halctf.tools.base import ToolRegistry

logger = logging.getLogger("halctf.runner")

TASK_TEMPLATE = """次の CTF チャレンジのフラグを取得して提出してください。

{brief}
{targets}
方針:
- 環境変数にフラグがある場合は read_env で読む。
- web 標的なら http_request で偵察・攻略する（SQLi は url のクエリ、XXE/deserialize は
  POST の body、JWT は Authorization ヘッダ。robots.txt も確認）。
- 攻撃対象は上記の『標的』だけ。127.0.0.1:9000（sidecar/MCP/推論）は自分の補助基盤
  なので絶対に攻撃・アクセスしない。
- 確信の持てるフラグが得られたら flag_submit で提出する。誤提出は避ける。"""

_ENV_FLAG_HINT = re.compile(r"\b(FLAG_[A-Z0-9_]+|BONUS_FLAG)\b")

_URL_RE = re.compile(r"https?://[^\s'\"]+")
_HOSTPORT_RE = re.compile(r"^[\w.-]+:\d{2,5}$")

# カテゴリ別の攻略プレイブック（小型モデルに定石を与える）。認可された CTF 競技用。
_PLAYBOOKS: list[tuple[tuple[str, ...], str]] = [
    (("sql",),
     "SQLi手順: (1)列数特定 ' UNION SELECT 1,2,3,...-- で200になる列数を探す。"
     "(2)DB判定: information_schema/database()/@@version が500ならSQLite。"
     "(3)テーブル列挙: SQLite→' UNION SELECT 1,name,3 FROM sqlite_master WHERE type='table'-- 、"
     "MySQL→information_schema.tables、Postgres→pg_tables。"
     "(4)非公開テーブルを ' UNION SELECT 1,<列>,3 FROM <table>-- でダンプし可視列で flag を読む。"),
    (("ssrf",),
     "SSRF: 到達可能サービス(ferry)の url パラメータに内部サービスを代理アクセスさせ応答から flag。"
     "内部指定は まずサービス名 http://underworld:PORT/ を試す(内部DNSで解決しIPフィルタを回避)。"
     "効かねばIP別表記: 10進 http://<整数IP>:PORT、16進 http://0xXXXXXXXX:PORT、"
     "IPv6射影 http://[::ffff:IP]:PORT。403=フィルタ拒否→別表記、502=到達失敗→ホスト/ポート見直し。"
     "サンドボックスは外部DNS無し(nip.io等は不可)。169.254.169.254 も一応試す。"),
    (("xxe",),
     "XXE: POST する XML に外部実体を仕込む: "
     "<!DOCTYPE r [<!ENTITY x SYSTEM \"file:///flag\">]><r>&x;</r>。応答に展開される。"),
    (("auth", "jwt"),
     "JWT(RS256→HS256混同): /pubkey や /.well-known で公開鍵PEMを取得。"
     "**取得したPEM文字列そのものをHMAC鍵**に HS256 で署名する(pyjwtを使う: "
     "jwt.encode({'role':'admin','username':'admin'}, pem_str, algorithm='HS256'))。"
     "PEMは取得バイトそのまま/末尾改行有無/BEGIN-END込みを数通り試す。alg=none(署名空)も試す。"
     "得たトークンを Authorization: Bearer で保護ページ(/flag)に付ける。hmac手組みは避ける。"),
    (("deser", "serial"),
     "Deserialization: run_python で pickle 等のペイロードを生成(__reduce__ でコマンド)、"
     "base64 して該当パラメータへ POST する。"),
    (("protocol", "reverse"),
     "Protocol RE: run_python の socket で接続。与えられたクライアント断片を参考に"
     "フレーミングを再現し、残り 1/3 のやり取りを実装する。"),
    (("forensic", "pcap"),
     "Forensics: 与えられた pcap/ファイルを run_python(urllib)で取得し、"
     "バイト列/ストリームを走査して flag を探す。"),
    (("cloud", "iam"),
     "Cloud/IAM(多段role assume): /whoami で現role、/roles で各roleと信頼関係(誰が誰をassume可)"
     "を読む。intern から flag 保持 role までの信頼チェーンを設計し、その順に POST /assume で"
     "1つずつ昇格する。403=その role は現 role を信頼しない(順序違い)→別の中継 role を経由。"
     "429=速すぎ→間隔を空け同じ失敗を繰り返さない。存在しないパスを闇雲に叩かない。"
     "最終 role に到達したら /flag 等を読む。"),
]


def playbook_for_category(category: str) -> str:
    cat = (category or "").lower()
    for keys, tip in _PLAYBOOKS:
        if any(k in cat for k in keys):
            return tip
    return ""


# 標的候補から除外する自分の補助基盤（sidecar/推論/MCP）。攻撃対象ではない。
_INFRA_KEYS = {"MCP_ENDPOINT", "OPENAI_BASE_URL", "HAL_MCP_HINT", "HAL_SIDECAR_URL"}


def target_hints_from_env() -> list[str]:
    """env から標的アドレスを組み立てて LLM に渡す。

    標的は `HAL_TARGET_IP`+`HAL_TARGET_PORT`（単一）だけでなく、
    `HAL_TARGET_<名前>_IP`+`HAL_TARGET_<名前>_PORT`（複数サービス, 例 FERRY/UNDERWORLD）
    で来ることがある。全て URL 化して渡す。自分の補助基盤(sidecar/MCP/推論)は除外する。
    """
    env = os.environ
    hints: list[str] = []
    # HAL_TARGET(_<名前>)_IP / _PORT のペアを全て拾う
    for ipk in sorted(k for k in env if k.startswith("HAL_TARGET") and k.endswith("_IP")):
        ip = env.get(ipk)
        if not ip:
            continue
        port = env.get(ipk[:-3] + "_PORT")  # _IP -> _PORT
        name = ipk[len("HAL_TARGET"):-3].strip("_")
        base = f"http://{ip}:{port}" if port else f"http://{ip}"
        hints.append(f"標的{('(' + name + ')') if name else ''} = {base}")
    # 汎用スキャン（別名で来た標的の取りこぼし防止）。基盤・フラグ・sidecar は除外。
    for k, v in sorted(env.items()):
        if not isinstance(v, str) or k in _INFRA_KEYS:
            continue
        if k.startswith("HAL_TARGET") or k.upper().startswith(("FLAG_", "BONUS_FLAG")):
            continue
        val = v.strip()
        if "127.0.0.1:9000" in val:  # sidecar 基盤
            continue
        if _URL_RE.search(val) or _HOSTPORT_RE.match(val):
            hints.append(f"{k}={val[:200]}")
    return hints[:12]


@dataclass
class ChallengeOutcome:
    challenge_id: str
    solved: bool
    flag: str | None
    steps: int
    reason: str


def challenge_from_env(settings) -> Challenge | None:
    """HAL_CHALLENGE_* からチャレンジを組む（注入されていれば）。"""
    cid = getattr(settings, "hal_challenge_id", None)
    if not cid:
        return None
    return Challenge(
        id=str(cid),
        name=getattr(settings, "hal_challenge_name", "") or "",
        category=getattr(settings, "hal_challenge_category", "") or "",
        description=getattr(settings, "hal_challenge_description", "") or "",
        extra={"slug": getattr(settings, "hal_challenge_slug", "") or ""},
    )


def obvious_env_flag(ch: Challenge) -> str | None:
    """env に直接置かれたフラグを見つける（Bonus / FLAG_<id> / 説明中の変数名）。

    LLM を介さず確実・高速に取れる env 系チャレンジ用。見つからなければ None。
    """
    cat = (ch.category or "").lower()
    slug = str(ch.extra.get("slug", "")).lower()
    # Bonus チャレンジ → BONUS_FLAG
    bonus = os.environ.get("BONUS_FLAG")
    if bonus and ("bonus" in cat or "bonus" in slug):
        return bonus
    # FLAG_<challenge_id>
    v = os.environ.get(f"FLAG_{ch.id}")
    if v:
        return v
    # 説明文が具体的な env 変数名に言及していれば（例「read FLAG_1」）
    m = _ENV_FLAG_HINT.search(ch.description or "")
    if m:
        v = os.environ.get(m.group(1))
        if v:
            return v
    return None


class AgentRunner:
    def __init__(
        self,
        client: LLMClient,
        challenges: ChallengeService,
        submitter: Submitter,
        settings,
        *,
        registry: ToolRegistry | None = None,
        target=None,
    ) -> None:
        self.client = client
        self.challenges = challenges
        self.submitter = submitter
        self.settings = settings
        # 明示指定があればそれを使い、無ければチャレンジのカテゴリで出し分ける。
        self._explicit_registry = registry
        self.target = target

    def solve_challenge(self, ch: Challenge, *, deadline: float) -> ChallengeOutcome:
        ctx = ToolContext(
            target=self.target,
            submitter=self.submitter,
            settings=self.settings,
            challenge_id=ch.id,
        )
        registry = self._explicit_registry or registry_for_category(ch.category)
        logger.info("道具: %s（category=%s）", registry.names(), ch.category)
        agent = ReactAgent(
            client=self.client,
            registry=registry,
            ctx=ctx,
            max_steps=self.settings.max_steps,
            run_budget_sec=self.settings.run_budget_sec,
        )
        agent.emit_completion = False  # 完了通知は runner が最後にまとめて出す
        hints = target_hints_from_env()
        targets = ("\n利用可能な標的（env より）:\n" + "\n".join(hints) + "\n") if hints else ""
        if hints:
            logger.info("標的候補: %s", hints)
        play = playbook_for_category(ch.category)
        if play:
            targets += f"定石: {play}\n"
        task = TASK_TEMPLATE.format(brief=ch.brief(), targets=targets)
        result = agent.solve(task, deadline=deadline)
        logger.info("challenge %s: solved=%s reason=%s", ch.id, result.solved, result.reason)
        return ChallengeOutcome(ch.id, result.solved, result.flag, result.steps, result.reason)

    def _discover(self) -> list[Challenge]:
        """env 優先でチャレンジを確定。無ければ MCP にフォールバック。"""
        env_ch = challenge_from_env(self.settings)
        if env_ch is not None:
            logger.info("env からチャレンジ確定: id=%s name=%s", env_ch.id, env_ch.name)
            return [env_ch]
        try:
            chs = [c for c in self.challenges.list_challenges() if not c.solved]
        except Exception as e:
            logger.error("MCP チャレンジ探索に失敗: %s", e)
            return []
        chs.sort(key=lambda c: (c.points if c.points is not None else 0))
        return chs

    def run(self, *, max_challenges: int | None = None) -> list[ChallengeOutcome]:
        announce_user_id(self.settings.user_id)
        log_identity_env()  # uid/challenge/model の注入 env を初回ログで確認
        # ingest の起動検証(HAL_DRY_RUN)では USER ID を出せれば良い。探索/推論はせず即終了。
        if getattr(self.settings, "dry_run", False):
            logger.info("dry-run: 起動検証のみ。探索・推論はスキップ。")
            return []
        deadline = time.monotonic() + self.settings.run_budget_sec
        outcomes: list[ChallengeOutcome] = []

        with Heartbeat(self.settings.heartbeat_sec):
            todo = self._discover()
            logger.info("対象: %d 問", len(todo))

            for i, ch in enumerate(todo):
                if max_challenges is not None and i >= max_challenges:
                    break
                if time.monotonic() > deadline:
                    logger.info("予算超過につき打ち切り")
                    break

                # fast-path: env に直接あるフラグは LLM 抜きで即提出
                flag = obvious_env_flag(ch)
                if flag:
                    accepted, msg = self.submitter.submit(ch.id, flag)
                    logger.info("fast-path 提出 %s -> %s (%s)", ch.id, accepted, msg)
                    outcomes.append(
                        ChallengeOutcome(
                            ch.id, accepted, flag if accepted else None, 0,
                            "fast-path" if accepted else "fast-path-rejected",
                        )
                    )
                    continue

                # それ以外は ReAct（web など）
                outcomes.append(self.solve_challenge(ch, deadline=deadline))

            self.submitter.done()
        return outcomes
