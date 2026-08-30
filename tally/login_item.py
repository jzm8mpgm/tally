"""Start Tally when the writer logs in.

Implemented with a plain LaunchAgent so it works identically whether Tally
is running from a built .app or straight from the source tree, and needs no
extra dependency.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys

LABEL = "com.mattmorgan.tally"


def _agents_dir() -> str:
    path = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(path, exist_ok=True)
    return path


def _plist_path() -> str:
    return os.path.join(_agents_dir(), f"{LABEL}.plist")


def _program_arguments() -> list[str]:
    executable = os.path.realpath(sys.executable)
    if ".app/Contents/MacOS/" in executable:
        return [executable]
    package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return [executable, "-m", "tally"]


def is_enabled() -> bool:
    return os.path.exists(_plist_path())


def set_enabled(enabled: bool) -> bool:
    """Turn the login item on or off. Returns the resulting state."""
    path = _plist_path()
    if not enabled:
        if os.path.exists(path):
            subprocess.run(
                ["launchctl", "unload", "-w", path],
                capture_output=True,
                check=False,
            )
            try:
                os.unlink(path)
            except OSError:
                pass
        return False

    package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    payload = {
        "Label": LABEL,
        "ProgramArguments": _program_arguments(),
        "RunAtLoad": True,
        "KeepAlive": False,
        "ProcessType": "Interactive",
        "WorkingDirectory": package_root,
    }
    try:
        with open(path, "wb") as handle:
            plistlib.dump(payload, handle)
    except OSError:
        return False

    subprocess.run(
        ["launchctl", "load", "-w", path], capture_output=True, check=False
    )
    return True
