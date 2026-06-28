"""
Newton-X configuration — single source of truth for all paths and settings.
Loaded from ~/.newton-x/config.json (created by 'newton init') or env vars.
"""

import json, os
from pathlib import Path

CONFIG_DIR = Path(os.getenv("NEWTON_CONFIG_DIR", Path.home() / ".newton-x"))
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULTS = {
    "raw_stream": str(CONFIG_DIR / "newton_raw.jsonl"),
    "audit_stream": str(CONFIG_DIR / "audit_stream.jsonl"),
    "thinking_stream": str(CONFIG_DIR / "thinking_stream.jsonl"),
    "task_file": str(CONFIG_DIR / "newton_task.jsonl"),
    "behavior_state": str(CONFIG_DIR / "behavior_state.json"),
    "pid_file": str(CONFIG_DIR / "newton_monitor.pid"),
    "api_key": "",
    "model": "deepseek-v4-flash",
    "api_url": "https://api.deepseek.com/v1/chat/completions",
    "intuition_interval": 5,
}


def load() -> dict:
    """Load config from file, falling back to env vars, then defaults."""
    config = dict(DEFAULTS)

    # File overrides
    if CONFIG_FILE.exists():
        try:
            file_config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            config.update(file_config)
        except (json.JSONDecodeError, KeyError):
            pass

    # Env var overrides (highest priority)
    env_map = {
        "NEWTON_RAW_STREAM": "raw_stream",
        "NEWTON_AUDIT_STREAM": "audit_stream",
        "NEWTON_THINKING_STREAM": "thinking_stream",
        "NEWTON_TASK_FILE": "task_file",
        "NEWTON_BEHAVIOR_STATE": "behavior_state",
        "DEEPSEEK_API_KEY": "api_key",
        "DEEPSEEK_MODEL": "model",
        "DEEPSEEK_API_URL": "api_url",
        "NEWTON_INTUITION_INTERVAL": "intuition_interval",
    }
    for env_var, config_key in env_map.items():
        val = os.getenv(env_var)
        if val:
            config[config_key] = val

    return config


def init_config(api_key: str = "", model: str = "deepseek-v4-flash"):
    """Create config directory and file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config = dict(DEFAULTS)
    if api_key:
        config["api_key"] = api_key
    if model:
        config["model"] = model
    CONFIG_FILE.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
    return config


def get(key: str, default=None):
    """Get a single config value."""
    return load().get(key, default)
