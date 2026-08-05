# HalCTF API（仮スキーマ — 未確定）

> ⚠️ これは**推測に基づく仮**。Player Preview で確定次第、正式値に置き換える。
> コードの既定値（`halctf/config.py`）はこの仮に合わせてある。

## 1. model query（OpenAI 互換を想定）

```
POST {MODEL_BASE_URL}/chat/completions
Authorization: Bearer {API_KEY}

{
  "model": "Llama-3.2-3B",
  "messages": [{"role": "user", "content": "..."}],
  "tools": [ ... ],          // function-calling
  "tool_choice": "auto",
  "temperature": 0.2
}
```

レスポンス: OpenAI 標準の `choices[0].message`（`content` / `tool_calls`）を想定。

## 2. flag submission（未確定）

```
POST {SUBMIT_BASE_URL}/submit
{ "flag": "flag{...}" }

→ { "correct": true, "message": "..." }   // 受理フィールド名は要確認
```

## 3. completion signal（未確定）

```
POST {SUBMIT_BASE_URL}/complete
{ "status": "done" }
```

## 4. モデル指定・加点

- 使用モデルは `model` パラメータで指定（想定）。
- 小型モデルほど高得点。加点式は要確認 → 確定したら多段フォールバックの
  切替閾値設計に反映する（`HALCTF_MODEL_CHAIN`）。

## 5. フラグ形式

- 仮: `flag\{[^}]+\}`（`HALCTF_FLAG_REGEX`）。実形式に差し替える。
