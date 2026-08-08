# HalCTF API（Help より・確定）

> Help ページで確定した実仕様。コードの既定値（`halctf/config.py`）はこれに合わせてある。
> 残る未確定は「USER ID の正確な env キー名」「MCP のワイヤ形式詳細」「/submit の受理フィールド名」
> 「BONUS_FLAG の対象 challenge_id」— 現地で `--smoke` 等で確認する。

## 実行時に注入される env（読むだけ。export しない）

| 変数 | 用途 |
|---|---|
| `OPENAI_BASE_URL` | 推論（OpenAI 互換）。sidecar が中継 |
| `MCP_ENDPOINT` | チャレンジ探索 / 提出の MCP サーバ |
| `HAL_*` | 実行アイデンティティ（USER ID を含む） |
| `BONUS_FLAG` | 提出パイプラインのスモークテスト用フラグ |
| `FLAG_1` 等 | チャレンジ固有（例 STARTER Flag 1） |

## 1. 推論（model query）

```
POST {OPENAI_BASE_URL}/chat/completions     # api_key は "not-needed"
{ "model": "llama3-2", "messages": [...], "tools": [...] }
```

モデル: `llama3-2` / `llama-3.1-8b` / `qwen3.6-35b-a3b`（gce-gpu-cluster・同時4）、
`google/gemma-4-26b-a4b-it-maas`（256K・同時無制限）。

## 2. フラグ提出（sidecar 簡易経路）

```
POST http://127.0.0.1:9000/submit
{ "challenge_id": "...", "flag": "flag{...}" }
→ 受理判定フィールドは要確認（correct / accepted / solved のいずれか想定）
```

## 3. 完了通知

```
POST http://127.0.0.1:9000/done
```

## 4. チャレンジ探索 / ヒント（MCP）

```
POST {MCP_ENDPOINT}   # JSON-RPC tools/call
tools: list_ctfs / list_challenges / get_challenge / get_challenge_status /
       submit_flag / request_hint / get_scoreboard / get_score_breakdown
```

## 5. 起動要件

- 起動30秒以内に `USER ID: <uid>` を stdout（本人確認 lint ゲート）
- stdout 無音2分でハング扱い（heartbeat）。`flush` 必須。`ENTRYPOINT` は `python -u`。

## 6. ネットワーク / リソース

- 到達可能: sidecar `127.0.0.1:9000` と現 CTF のサブネットのみ（外部インターネット無し）
- run 1h / tarball 2560MB / mem 512Mi–2Gi / CPU 500m–2 / storage 4–8Gi / team 5
