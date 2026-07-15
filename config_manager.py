"""Configuration management for GitHub Trending Reporter."""

import json
from pathlib import Path
import os

CONFIG_DIR = Path.home() / ".github_trending_reporter"
CONFIG_FILE = CONFIG_DIR / "config.json"
HISTORY_DIR = CONFIG_DIR / "history"


def get_default_config():
    return {
        "schedule": {
            "interval_type": "daily",
            "interval_value": 1,
            "check_time": "09:00",
            "check_day_of_week": "1",
        },
        "agent": {
            "name": "",
            "command": "",
            "prompt_args": [],
            "timeout": 300,
            "args_overridden": [],
       },
        "email": {
            "provider": "gmail",
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587,
            "username": "",
            "password": "",
            "use_tls": True,
            "recipients": [],
            "sender_name": "GitHub Trending Reporter",
        },
        "trending": {
            "time_range": "daily",
            "language": "",
            "spoken_language": "",
        },
        "filters": {
            "min_stars": 0,
            "min_stars_today": 0,
            "max_repos": 25,
            "exclude_keywords": [],
            "include_keywords": [],
        },
        "report": {
            "include_charts": True,
            "include_agent_analysis": True,
            "report_style": "detailed",
            "language": "en",
        },
        "app": {
            "minimize_to_tray": True,
            "run_in_background": True,
            "start_on_boot": False,
           "check_on_startup": False,
          "history_keep_days": 90,
      },
    }


def _deep_merge(default, saved):
    result = default.copy()
    for key, val in saved.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = _deep_merge(result[key], val)
        else:
            result[key] = val
    return result


def load_config():
    default = get_default_config()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config = _deep_merge(default, saved)
            _migrate_config(config)
            return config
        except (json.JSONDecodeError, IOError):
            pass
    return default


def _migrate_config(config):
    """Migrate old config values to new format.

    - Replace invalid Amp arg '--print' with '-x'.
    """
    agent = config.get("agent", {})
    args = agent.get("prompt_args", [])
    if "--print" in args:
        agent["prompt_args"] = ["-x" if a == "--print" else a for a in args]
        config["agent"] = agent


def save_config(config):
    _migrate_config(config)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    # Restrict file permissions — config contains SMTP credentials
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except OSError:
        pass  # Windows may handle permissions differently


def validate_config(config):
    errors = []
    email = config.get("email", {})
    if not email.get("username"):
        errors.append("Email username is required.")
    if not email.get("password"):
        errors.append("Email password / app password is required.")
    if not email.get("recipients"):
        errors.append("At least one recipient email is required.")
    agent = config.get("agent", {})
    if not agent.get("command"):
        errors.append("An AI agent must be selected.")
    sched = config.get("schedule", {})
    if sched.get("interval_type") == "custom_days":
        val = sched.get("interval_value", 1)
        if not (1 <= val <= 30):
            errors.append("Custom days interval must be between 1 and 30.")
    if sched.get("interval_type") == "custom_weeks":
        val = sched.get("interval_value", 1)
        if not (1 <= val <= 30):
            errors.append("Custom weeks interval must be between 1 and 30.")
    return errors


def ensure_dirs():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def get_history_dir():
    return HISTORY_DIR


def get_config_dir():
    return CONFIG_DIR
