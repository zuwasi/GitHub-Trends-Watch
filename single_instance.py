"""Cross-platform single-instance lock for GitHub Trends Watch.

On Windows: uses a named mutex (kernel object, auto-released on exit).
On Linux/macOS: uses an exclusive flock on a lock file in the config dir.
"""

import sys
import os

LOCK_NAME = "GitHubTrendsWatch_SingleInstance"


def _try_lock_windows():
    """Try to acquire a named mutex on Windows. Returns True if acquired."""
    import ctypes
    from ctypes import wintypes

    ERROR_ALREADY_EXISTS = 183

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CreateMutexW.argtypes = [wintypes.LPCVOID, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.GetLastError.restype = wintypes.DWORD

    handle = kernel32.CreateMutexW(None, False, LOCK_NAME)
    if kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
        return False
    globals()["_win_mutex_handle"] = handle
    return True


def _try_lock_unix():
    """Try to acquire an exclusive file lock on Linux/macOS. Returns True if acquired."""
    import fcntl
    from config_manager import get_config_dir

    lock_path = get_config_dir() / "single_instance.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except (BlockingIOError, OSError):
        os.close(fd)
        return False
    globals()["_unix_lock_fd"] = fd
    return True


def acquire():
    """Return True if this is the first instance, False if another is already running."""
    if sys.platform == "win32":
        return _try_lock_windows()
    else:
        return _try_lock_unix()
