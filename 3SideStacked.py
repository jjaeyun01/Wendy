#!/usr/bin/env python3
"""
3SideStacked.py
Arranges the 3 windows on the current workspace into Side + Stacked layout.

+------------+------------+
|            |     B      |
|     A      |            |
|            +------------+
|            |     C      |
|            |            |
+------------+------------+
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _run_aerospace(argv: list[str]) -> int:
    r = subprocess.run(["aerospace", *argv], cwd=str(ROOT))
    return int(r.returncode)


def _get_current_workspace() -> str:
    out = subprocess.run(
        ["aerospace", "list-workspaces", "--focused"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    return out.stdout.strip()


def _get_windows_on_workspace(workspace: str) -> list[dict]:
    out = subprocess.run(
        ["aerospace", "list-windows", "--workspace", workspace, "--json"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if out.returncode != 0:
        return []
    try:
        return json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return []


def main() -> None:
    ws = _get_current_workspace()
    print(f"\n  3SideStacked — workspace {ws}")

    windows = _get_windows_on_workspace(ws)
    if len(windows) < 3:
        print(f"  ✗ Need 3 windows, found {len(windows)}")
        return

    id_a = windows[0]["window-id"]
    id_b = windows[1]["window-id"]
    id_c = windows[2]["window-id"]

    print(f"  A={windows[0].get('app-name')}  B={windows[1].get('app-name')}  C={windows[2].get('app-name')}\n")

    time.sleep(2.0)

    # Focus A, split horizontally → A left, rest right
    _run_aerospace(["focus", "--window-id", str(id_a)])
    time.sleep(0.3)
    _run_aerospace(["layout", "tiles", "horizontal"])
    time.sleep(0.3)

    # Focus B, split vertically → B top right, C bottom right
    _run_aerospace(["focus", "--window-id", str(id_b)])
    time.sleep(0.3)
    _run_aerospace(["layout", "tiles", "vertical"])
    time.sleep(0.3)

    # Move C into B's container
    _run_aerospace(["focus", "--window-id", str(id_c)])
    time.sleep(0.3)
    _run_aerospace(["move-node-to-window-container"])

    # Focus back on A
    _run_aerospace(["focus", "--window-id", str(id_a)])

    print("  ✓ Done.\n")


if __name__ == "__main__":
    main()