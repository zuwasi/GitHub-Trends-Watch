"""Detect AI coding agents installed on the system."""

import shutil
import subprocess
import sys
from pathlib import Path

# Registry of known agents and how to invoke them in non-interactive mode.
KNOWN_AGENTS = {
    "amp": {
        "display_name": "Amp",
        "command": "amp",
        "prompt_args": ["-x"],
        "version_args": ["--version"],
    },
    "claude": {
        "display_name": "Claude Code",
        "command": "claude",
        "prompt_args": ["-p"],
        "version_args": ["--version"],
    },
    "gemini": {
        "display_name": "Gemini CLI",
        "command": "gemini",
        "prompt_args": [],
        "version_args": ["--version"],
    },
    "codex": {
        "display_name": "Codex CLI",
        "command": "codex",
        "prompt_args": ["--prompt"],
        "version_args": ["--version"],
    },
    "aider": {
        "display_name": "Aider",
        "command": "aider",
        "prompt_args": ["--message"],
        "version_args": ["--version"],
    },
    "gh": {
        "display_name": "GitHub Copilot CLI",
        "command": "gh",
        "prompt_args": ["copilot", "suggest"],
        "version_args": ["--version"],
    },
    "opencode": {
        "display_name": "OpenCode",
        "command": "opencode",
        "prompt_args": ["--prompt"],
        "version_args": ["--version"],
    },
    "crush": {
        "display_name": "Crush",
        "command": "crush",
        "prompt_args": ["--prompt"],
        "version_args": ["--version"],
    },
    "yi": {
        "display_name": "Yi CLI",
        "command": "yi",
        "prompt_args": ["--prompt"],
        "version_args": ["--version"],
    },
}

# Extra paths to check on each OS (beyond PATH).
EXTRA_PATHS = {
    "win32": [
        Path.home() / "AppData" / "Local" / "Programs" / "amp" / "amp.exe",
        Path.home() / "AppData" / "Roaming" / "npm" / "amp.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "claude.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "gemini.cmd",
        Path.home() / "AppData" / "Roaming" / "npm" / "codex.cmd",
        Path.home() / "AppData" / "Local" / "Programs" / "claude" / "claude.exe",
    ],
    "darwin": [
        Path.home() / ".local" / "bin" / "amp",
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/amp"),
        Path("/usr/local/bin/claude"),
        Path("/opt/homebrew/bin/amp"),
        Path("/opt/homebrew/bin/claude"),
    ],
    "linux": [
        Path.home() / ".local" / "bin" / "amp",
        Path.home() / ".local" / "bin" / "claude",
        Path("/usr/local/bin/amp"),
        Path("/usr/local/bin/claude"),
        Path("/usr/bin/amp"),
        Path("/usr/bin/claude"),
    ],
}


def _find_executable(name):
    """Find an executable in PATH or in known extra locations."""
    found = shutil.which(name)
    if found:
        return found
    platform_key = sys.platform
    for extra in EXTRA_PATHS.get(platform_key, []):
        # Match by stem (e.g. 'amp' matches 'amp.exe').
        if extra.stem == name and extra.exists():
            return str(extra)
    return None


def detect_agents():
    """Return a list of dicts describing each detected agent.

    Each dict has: key, display_name, command, prompt_args, path.
    """
    detected = []
    for key, info in KNOWN_AGENTS.items():
        path = _find_executable(info["command"])
        if path:
            detected.append({
                "key": key,
                "display_name": info["display_name"],
                "command": path if path != info["command"] else info["command"],
                "prompt_args": info["prompt_args"],
                "path": path,
            })
    return detected


def get_agent_info(key):
    """Return the registry entry for a known agent key, or None."""
    return KNOWN_AGENTS.get(key)
