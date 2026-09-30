import configparser
import os
from pathlib import Path

from kbflow.toon import toon_loads

_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"


def load_projects(path):
    with open(path, "r", encoding="utf-8") as handle:
        return toon_loads(handle.read())


def _load_env_file():
    for env_file in (Path.cwd() / ".env", Path.home() / ".kbflow.env"):
        if not env_file.exists():
            continue
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = val


def _config_ini_paths():
    return (Path.cwd() / ".kbflow" / "config.ini", Path.home() / ".kbflow" / "config.ini")


def _load_config_file():
    cfg = {}
    for path in _config_ini_paths():
        if not path.exists():
            continue
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8")
        if parser.has_section("llm"):
            for key in ("api_key", "base_url", "model"):
                if parser.has_option("llm", key):
                    cfg[key] = parser.get("llm", key).strip()
    return cfg


def get_llm_config():
    _load_env_file()
    cfg = _load_config_file()
    return {
        "base_url": os.environ.get("KBFLOW_LLM_BASE_URL", cfg.get("base_url", _DEFAULT_BASE_URL)),
        "api_key": os.environ.get("KBFLOW_LLM_API_KEY", cfg.get("api_key", "")),
        "model": os.environ.get("KBFLOW_LLM_MODEL", cfg.get("model", _DEFAULT_MODEL)),
    }


def get_database_config():
    _load_env_file()
    db = {"mcp_command": "", "mcp_args": "", "mcp_cwd": "", "env": {}}
    for path in _config_ini_paths():
        if not path.exists():
            continue
        parser = configparser.ConfigParser()
        parser.read(path, encoding="utf-8")
        if parser.has_section("database"):
            if parser.has_option("database", "mcp_command"):
                db["mcp_command"] = parser.get("database", "mcp_command").strip()
            if parser.has_option("database", "mcp_args"):
                db["mcp_args"] = parser.get("database", "mcp_args").strip()
            if parser.has_option("database", "mcp_cwd"):
                db["mcp_cwd"] = parser.get("database", "mcp_cwd").strip()
        if parser.has_section("database.env"):
            for key, val in parser.items("database.env"):
                db["env"][key.upper()] = val.strip()
    return db
