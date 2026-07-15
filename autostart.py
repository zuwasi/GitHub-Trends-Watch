"""Cross-platform auto-start management.

Registers the app to launch after system restart on:
- Windows: Registry key in HKCU/Software/Microsoft/Windows/CurrentVersion/Run
- Linux: .desktop file in ~/.config/autostart/
- macOS: LaunchAgent plist in ~/Library/LaunchAgents/
"""

import sys
import os
from pathlib import Path

APP_NAME = "GitHubTrendsWatch"


def _get_executable_path():
    """Return the path to the executable or Python script to launch."""
    if getattr(sys, "frozen", False):
        # Running as PyInstaller exe
        return sys.executable
    else:
        # Running from source — use main.py with python
        main_py = Path(__file__).parent / "main.py"
        return f'"{sys.executable}" "{main_py}" --background'


def enable_autostart():
    """Register the app to start on system boot.

    Returns (success: bool, message: str).
    """
    platform = sys.platform
    if platform == "win32":
        return _enable_windows()
    elif platform == "darwin":
        return _enable_macos()
    else:
        return _enable_linux()


def disable_autostart():
    """Remove the app from system auto-start.

    Returns (success: bool, message: str).
    """
    platform = sys.platform
    if platform == "win32":
        return _disable_windows()
    elif platform == "darwin":
        return _disable_macos()
    else:
        return _disable_linux()


def is_autostart_enabled():
    """Check if auto-start is currently registered."""
    platform = sys.platform
    if platform == "win32":
        return _is_enabled_windows()
    elif platform == "darwin":
        return _is_enabled_macos()
    else:
        return _is_enabled_linux()


# --- Windows ---

def _enable_windows():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        exe_path = _get_executable_path()
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
        return True, "Auto-start enabled (Windows registry)"
    except Exception as e:
        return False, f"Failed to enable auto-start: {e}"


def _disable_windows():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True, "Auto-start disabled"
    except FileNotFoundError:
        return True, "Auto-start was not registered"
    except Exception as e:
        return False, f"Failed to disable auto-start: {e}"


def _is_enabled_windows():
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ,
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False


# --- macOS ---

def _get_plist_path():
    return Path.home() / "Library" / "LaunchAgents" / f"com.{APP_NAME}.plist"


def _enable_macos():
    try:
        plist_dir = Path.home() / "Library" / "LaunchAgents"
        plist_dir.mkdir(parents=True, exist_ok=True)
        plist_path = _get_plist_path()
        exe_path = _get_executable_path()
        label = f"com.{APP_NAME}"
        plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{exe_path}</string>
        <string>--background</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>
"""
        plist_path.write_text(plist_content, encoding="utf-8")
        return True, "Auto-start enabled (macOS LaunchAgent)"
    except Exception as e:
        return False, f"Failed to enable auto-start: {e}"


def _disable_macos():
    try:
        plist_path = _get_plist_path()
        if plist_path.exists():
            plist_path.unlink()
        return True, "Auto-start disabled"
    except Exception as e:
        return False, f"Failed to disable auto-start: {e}"


def _is_enabled_macos():
    return _get_plist_path().exists()


# --- Linux ---

def _get_desktop_path():
    return Path.home() / ".config" / "autostart" / f"{APP_NAME}.desktop"


def _enable_linux():
    try:
        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)
        desktop_path = _get_desktop_path()
        exe_path = _get_executable_path()
        desktop_content = f"""[Desktop Entry]
Type=Application
Name=GitHub Trends Watch
Exec={exe_path} --background
Icon=system-search
Terminal=false
X-GNOME-Autostart-enabled=true
Categories=Utility;
"""
        desktop_path.write_text(desktop_content, encoding="utf-8")
        return True, "Auto-start enabled (Linux autostart)"
    except Exception as e:
        return False, f"Failed to enable auto-start: {e}"


def _disable_linux():
    try:
        desktop_path = _get_desktop_path()
        if desktop_path.exists():
            desktop_path.unlink()
        return True, "Auto-start disabled"
    except Exception as e:
        return False, f"Failed to disable auto-start: {e}"


def _is_enabled_linux():
    return _get_desktop_path().exists()
