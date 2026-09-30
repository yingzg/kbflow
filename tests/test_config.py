from kbflow.config import get_database_config, get_llm_config


def test_llm_config_from_ini(monkeypatch, tmp_path):
    for var in ("KBFLOW_LLM_API_KEY", "KBFLOW_LLM_BASE_URL", "KBFLOW_LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    ini = tmp_path / ".kbflow" / "config.ini"
    ini.parent.mkdir(parents=True)
    ini.write_text(
        "[llm]\napi_key = sk-test\nbase_url = https://api.example.com/v1\nmodel = my-model\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    cfg = get_llm_config()
    assert cfg["api_key"] == "sk-test"
    assert cfg["base_url"] == "https://api.example.com/v1"
    assert cfg["model"] == "my-model"


def test_llm_config_env_overrides_ini(monkeypatch, tmp_path):
    monkeypatch.setenv("KBFLOW_LLM_API_KEY", "sk-from-env")
    ini = tmp_path / ".kbflow" / "config.ini"
    ini.parent.mkdir(parents=True)
    ini.write_text("[llm]\napi_key = sk-from-ini\nmodel = ini-model\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cfg = get_llm_config()
    assert cfg["api_key"] == "sk-from-env"
    assert cfg["model"] == "ini-model"


def test_llm_config_defaults(monkeypatch, tmp_path):
    for var in ("KBFLOW_LLM_API_KEY", "KBFLOW_LLM_BASE_URL", "KBFLOW_LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.chdir(tmp_path)
    cfg = get_llm_config()
    assert cfg["api_key"] == ""
    assert cfg["base_url"] == "https://api.openai.com/v1"
    assert cfg["model"] == "gpt-4o-mini"


def test_database_config_from_ini(monkeypatch, tmp_path):
    ini = tmp_path / ".kbflow" / "config.ini"
    ini.parent.mkdir(parents=True)
    ini.write_text(
        "[database]\n"
        "mcp_command = ./toolbox\n"
        "mcp_args = --prebuilt oceanbase --stdio\n"
        "mcp_cwd = /root/.codex\n"
        "[database.env]\n"
        "OCEANBASE_DATABASE = test_db\n"
        "OCEANBASE_HOST = test-host.example.com\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    cfg = get_database_config()
    assert cfg["mcp_command"] == "./toolbox"
    assert cfg["mcp_args"] == "--prebuilt oceanbase --stdio"
    assert cfg["mcp_cwd"] == "/root/.codex"
    assert cfg["env"]["OCEANBASE_DATABASE"] == "test_db"


def test_database_config_empty_by_default(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    cfg = get_database_config()
    assert cfg["mcp_command"] == ""
