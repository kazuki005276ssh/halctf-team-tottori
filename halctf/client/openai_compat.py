"""OpenAI 互換クライアント（中央 Model Service 用）。

モデル多段切替（小型優先 → 難所フォールバック）を chat() レベルで扱う。
API 仕様確定後に微修正できるよう、パス・スキーマは狭い範囲に閉じ込める。
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from halctf.client.base import ChatMessage, ChatResult, ToolCall, ToolSpec

logger = logging.getLogger("halctf.client")


class OpenAICompatClient:
    """/chat/completions を叩く最小クライアント。"""

    def __init__(
        self,
        base_url: str,
        models: list[str],
        *,
        api_key: str = "not-needed",  # sidecar が実キーを注入するため不要
        timeout_sec: float = 90.0,
        max_retries: int = 2,
        pinned_model: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.models = models
        self.max_retries = max_retries
        # プラットフォームが HAL_AGENT_MODEL で指定したモデル。あれば /models 検出を省く。
        self.pinned_model = pinned_model
        self._available: set[str] | None = None
        self._resolved: str | None = None
        self._http = httpx.Client(
            base_url=self.base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout_sec,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def available_models(self) -> set[str]:
        """GET /models で提供モデル一覧を取得（OpenAI 互換）。失敗時は空集合。"""
        if self._available is not None:
            return self._available
        try:
            resp = self._http.get("/models")
            resp.raise_for_status()
            data = resp.json()
            ids = {m.get("id") for m in data.get("data", []) if isinstance(m, dict)}
            self._available = {i for i in ids if i}
        except (httpx.HTTPError, ValueError, KeyError) as e:
            logger.warning("/models 取得に失敗（チェーン先頭を使う）: %s", e)
            self._available = set()
        return self._available

    def resolved_model(self) -> str:
        """提供モデルのうち、優先チェーンで最初に使えるものを選ぶ。

        提供一覧が取れないときはチェーン先頭。どれも一致しないときは一覧の先頭。
        CTF ごとにモデル名が違っても不一致にならないための解決。
        """
        if self._resolved:
            return self._resolved
        if self.pinned_model:
            self._resolved = self.pinned_model
            logger.info("使用モデル: %s（HAL_AGENT_MODEL 指定）", self._resolved)
            return self._resolved
        avail = self.available_models()
        chosen = ""
        if avail:
            chosen = next((m for m in self.models if m in avail), sorted(avail)[0])
        elif self.models:
            chosen = self.models[0]
        self._resolved = chosen
        logger.info("使用モデル: %s（提供: %s）", chosen, sorted(avail) or "unknown")
        return chosen

    def __enter__(self) -> OpenAICompatClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def chat(
        self,
        messages: list[ChatMessage],
        *,
        tools: list[ToolSpec] | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        **kwargs: Any,
    ) -> ChatResult:
        """model 未指定なら提供モデルから自動解決（優先チェーン順）した1つを使う。"""
        chosen = model or self.resolved_model()
        payload: dict[str, Any] = {
            "model": chosen,
            "messages": [m.to_openai() for m in messages],
            "temperature": temperature,
        }
        if tools:
            payload["tools"] = [t.to_openai() for t in tools]
            payload["tool_choice"] = "auto"
        payload.update(kwargs)

        last_exc: Exception | None = None
        for attempt in range(self.max_retries + 1):
            try:
                resp = self._http.post("/chat/completions", json=payload)
                resp.raise_for_status()
                return self._parse(resp.json(), chosen)
            except (httpx.HTTPError, KeyError, ValueError) as e:
                last_exc = e
                wait = min(2**attempt, 8)
                logger.warning("chat 失敗 (attempt=%d, model=%s): %s", attempt, chosen, e)
                time.sleep(wait)
        raise RuntimeError(f"chat が {self.max_retries + 1} 回失敗: {last_exc}")

    @staticmethod
    def _parse(data: dict[str, Any], model: str) -> ChatResult:
        choice = data["choices"][0]
        msg = choice["message"]
        content = msg.get("content") or ""
        tool_calls: list[ToolCall] = []
        for tc in msg.get("tool_calls", []) or []:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments", "{}")
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                args = {"_raw": raw_args}
            tool_calls.append(
                ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), arguments=args or {})
            )
        return ChatResult(
            content=content,
            tool_calls=tool_calls,
            model=data.get("model", model),
            finish_reason=choice.get("finish_reason"),
        )
