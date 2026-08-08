from halctf.config import Settings


def test_reads_platform_env_names(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "http://proxy/llm")
    monkeypatch.setenv("MCP_ENDPOINT", "http://proxy/mcp")
    monkeypatch.setenv("HAL_USER_ID", "uid-123")
    monkeypatch.setenv("BONUS_FLAG", "flag{bonus}")
    s = Settings(_env_file=None)
    assert s.openai_base_url == "http://proxy/llm"
    assert s.mcp_endpoint == "http://proxy/mcp"
    assert s.user_id == "uid-123"
    assert s.bonus_flag == "flag{bonus}"


def test_halctf_prefix_overrides_local(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("HALCTF_OPENAI_BASE_URL", "http://local/llm")
    s = Settings(_env_file=None)
    assert s.openai_base_url == "http://local/llm"


def test_model_chain_parsing(monkeypatch):
    monkeypatch.setenv("HALCTF_MODEL_CHAIN", "llama3-2, qwen3.6-35b-a3b ,")
    s = Settings(_env_file=None)
    assert s.models == ["llama3-2", "qwen3.6-35b-a3b"]


def test_defaults_point_to_sidecar():
    s = Settings(_env_file=None)
    assert "127.0.0.1:9000" in s.sidecar_url
