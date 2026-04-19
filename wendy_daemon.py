#!/usr/bin/env python3
"""
Wendy daemon — keep the mic listener running (double-clap → config.json state).

  Foreground (dev):
    python3 wendy_daemon.py

  Install LaunchAgent (login item, auto-restart):
    python3 wendy_daemon.py --install-launchagent
    launchctl load ~/Library/LaunchAgents/com.wendy.daemon.plist

  Uninstall:
    launchctl unload ~/Library/LaunchAgents/com.wendy.daemon.plist
    rm ~/Library/LaunchAgents/com.wendy.daemon.plist
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PLIST_NAME = "com.wendy.daemon.plist"
LABEL = "com.wendy.daemon"


def _install_launchagent() -> None:
    py = Path(sys.executable).resolve()
    daemon = (ROOT / "wendy_daemon.py").resolve()
    out = Path.home() / "Library" / "LaunchAgents" / PLIST_NAME
    out.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "Label": LABEL,
        "ProgramArguments": [str(py), str(daemon), "--no-reinstall"],
        "WorkingDirectory": str(ROOT),
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(ROOT / "wendy.log"),
        "StandardErrorPath": str(ROOT / "wendy.err.log"),
    }
    out.write_bytes(plistlib.dumps(payload))
    print(f"  ✓ Wrote {out}")
    print("  Load with:  launchctl load ~/Library/LaunchAgents/" + PLIST_NAME)
    print("  Mic access: grant Terminal (or your Python host) in System Settings → Privacy → Microphone.\n")


def main() -> None:
    if "--install-launchagent" in sys.argv:
        _install_launchagent()
        return
    if "--no-reinstall" in sys.argv:
        pass

    from wake_word import build_from_config
    from clap_detector import run_forever

    wake = build_from_config()
    if wake is not None:
        if not wake.start():
            print("  ⚠  Wake word unavailable — clap detection always active")
            wake = None
    else:
        print("  ℹ  Wake word disabled in config — clap detection always active")

    run_forever(wake=wake)


if __name__ == "__main__":
    main()
