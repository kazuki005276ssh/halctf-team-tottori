import json

import httpx

from halctf.services.mcp import McpChallengeService
from halctf.services.sidecar import SidecarClient


# ---- sidecar ----
def _sidecar_handler(request: httpx.Request) -> httpx.Response:
    if request.url.path == "/submit":
        body = json.loads(request.content)
        correct = body.get("flag") == "flag{right}"
        return httpx.Response(200, json={"correct": correct, "message": "ok"})
    if request.url.path == "/done":
        return httpx.Response(200, json={})
    return httpx.Response(404)


def test_sidecar_submit_accepts_correct():
    c = SidecarClient(transport=httpx.MockTransport(_sidecar_handler))
    ok, _ = c.submit("c1", "flag{right}")
    assert ok


def test_sidecar_submit_rejects_wrong():
    c = SidecarClient(transport=httpx.MockTransport(_sidecar_handler))
    ok, _ = c.submit("c1", "flag{nope}")
    assert not ok


def test_sidecar_done_no_raise():
    c = SidecarClient(transport=httpx.MockTransport(_sidecar_handler))
    c.done()  # 例外を出さない


# ---- MCP ----
def _mcp_handler(request: httpx.Request) -> httpx.Response:
    body = json.loads(request.content)
    name = body["params"]["name"]
    rid = body["id"]
    if name == "list_challenges":
        payload = {"challenges": [
            {"id": "c1", "name": "Warmup", "category": "Misc", "points": 50},
            {"id": "c2", "name": "Web", "category": "Web", "points": 100},
        ]}
    elif name == "get_challenge":
        payload = {"id": "c1", "name": "Warmup", "category": "Misc",
                   "description": "read FLAG_1", "points": 50}
    else:
        payload = {}
    result = {"jsonrpc": "2.0", "id": rid,
              "result": {"content": [{"type": "text", "text": json.dumps(payload)}]}}
    return httpx.Response(200, json=result, headers={"content-type": "application/json"})


def test_mcp_list_challenges():
    svc = McpChallengeService("http://mcp", transport=httpx.MockTransport(_mcp_handler))
    chs = svc.list_challenges()
    assert [c.id for c in chs] == ["c1", "c2"]
    assert chs[0].points == 50


def test_mcp_get_challenge():
    svc = McpChallengeService("http://mcp", transport=httpx.MockTransport(_mcp_handler))
    c = svc.get_challenge("c1")
    assert c.id == "c1" and "FLAG_1" in c.description


# ---- model auto-discovery (client) ----
def test_client_resolves_available_model():
    import httpx as _httpx

    from halctf.client.openai_compat import OpenAICompatClient

    def handler(request):
        return _httpx.Response(200, json={"data": [
            {"id": "llama-3.1-8b"}, {"id": "qwen3.6-35b-a3b"},
        ]})

    c = OpenAICompatClient(
        "http://x", ["llama3-2", "qwen3.6-35b-a3b", "llama-3.1-8b"],
        transport=_httpx.MockTransport(handler),
    )
    # llama3-2 は提供にないので、チェーン優先順で次に使える qwen3.6-35b-a3b を選ぶ
    assert c.resolved_model() == "qwen3.6-35b-a3b"


def test_client_falls_back_when_models_unavailable():
    import httpx as _httpx

    from halctf.client.openai_compat import OpenAICompatClient

    def handler(request):
        return _httpx.Response(500)

    c = OpenAICompatClient(
        "http://x", ["llama-3.1-8b"], transport=_httpx.MockTransport(handler)
    )
    assert c.resolved_model() == "llama-3.1-8b"
