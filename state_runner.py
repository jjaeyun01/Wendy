#!/usr/bin/env python3
"""
state_runner.py
Applies Tony Stark's workspace state from settings.json.
Called by trigger — does not handle the trigger itself.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "configuration" / "settings.json"


def _load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        raise SystemExit(f"Missing settings.json at {SETTINGS_PATH}")
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def _get_bundle_id(settings: dict, app_key: str) -> str:
    """Resolve app key (e.g. 'ide') → bundle ID from settings.json apps section."""
    app = settings.get("apps", {}).get(app_key, {})
    if isinstance(app, dict):
        return app.get("bundle_id", "")
    return ""


def _run_aerospace(argv: list[str]) -> int:
    r = subprocess.run(["aerospace", *argv], cwd=str(ROOT))
    return int(r.returncode)


def _youtube_url_with_autoplay(url: str) -> str:
    u = url.strip()
    if not u or "autoplay=" in u.lower():
        return u
    host = (urlparse(u).hostname or "").lower()
    if "youtube.com" not in host and "youtu.be" not in host:
        return u
    parsed = urlparse(u)
    q = dict(parse_qsl(parsed.query, keep_blank_values=True))
    q["autoplay"] = "1"
    new_query = urlencode(q)
    return urlunparse(
        (parsed.scheme, parsed.netloc, parsed.path, parsed.params, new_query, parsed.fragment)
    )


def _list_windows_bundle_all_monitors(bundle_id: str) -> list[dict]:
    out = subprocess.run(
        ["aerospace", "list-windows", "--monitor", "all", "--app-bundle-id", bundle_id, "--json"],
        capture_output=True, text=True, cwd=str(ROOT),
    )
    if out.returncode != 0:
        return []
    try:
        return json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return []


def _move_active_workspaces_to_z(active_workspace_ids: list[str]) -> None:
    """Move windows only from active workspaces to workspace Z."""
    print(f"  → Clearing workspaces {active_workspace_ids} → Z")
    for ws_id in active_workspace_ids:
        out = subprocess.run(
            ["aerospace", "list-windows", "--workspace", ws_id, "--json"],
            capture_output=True, text=True, cwd=str(ROOT),
        )
        if out.returncode != 0:
            continue
        try:
            windows = json.loads(out.stdout or "[]")
        except json.JSONDecodeError:
            continue
        for w in windows:
            wid = w.get("window-id")
            if wid is None:
                continue
            _run_aerospace(["move-node-to-workspace", "--window-id", str(wid), "Z"])
    time.sleep(0.5)


def _ensure_bundle_on_workspace(workspace: str, bundle_id: str, cmd_delay: float) -> None:
    """If app already has windows, move them to workspace. Otherwise open it."""
    if not bundle_id:
        print(f"     ⚠ no bundle ID — skipping")
        return

    rows = _list_windows_bundle_all_monitors(bundle_id)
    if rows:
        for row in rows:
            wid = row.get("window-id")
            if wid is None:
                continue
            print(f"     move {row.get('app-name', '?')} → workspace {workspace}")
            _run_aerospace(["move-node-to-workspace", "--window-id", str(wid), workspace])
        time.sleep(cmd_delay)
        return

    print(f"     open bundle: {bundle_id}")
    subprocess.run(["open", "-b", bundle_id], cwd=str(ROOT))
    time.sleep(cmd_delay)


def _open_music_url(url: str) -> None:
    u = _youtube_url_with_autoplay(url)
    print(f"     music: Firefox → {u[:72]}{'…' if len(u) > 72 else ''}")
    subprocess.Popen(["open", "-a", "Firefox", u], cwd=str(ROOT), start_new_session=True)
    time.sleep(1.0)


def _apply_workspace(workspace: str, ws_data: dict, settings: dict, cmd_delay: float) -> None:
    print(f"\n  ⬤ Workspace {workspace}")

    # Switch to workspace
    _run_aerospace(["workspace", workspace])
    time.sleep(0.5)

    # Open apps
    apps = ws_data.get("apps", [])
    for app_key in apps:
        bundle_id = _get_bundle_id(settings, app_key)
        print(f"     app: {app_key} → {bundle_id or '(no bundle id)'}")
        _ensure_bundle_on_workspace(workspace, bundle_id, cmd_delay)

    # Open browser URL if present
    browser_url = ws_data.get("browser_url", "").strip()
    if browser_url:
        browser_bundle = _get_bundle_id(settings, "browser")
        print(f"     browser: → {browser_url[:72]}{'…' if len(browser_url) > 72 else ''}")
        subprocess.Popen(["open", "-b", browser_bundle, browser_url], cwd=str(ROOT), start_new_session=True)
        time.sleep(1.0)

    # Open music URL if present
    music_url = ws_data.get("music_url", "").strip()
    if music_url:
        _open_music_url(music_url)


def apply_state(user: str = "Tony Stark") -> None:
    settings = _load_settings()
    cmd_delay = 1.2

    state = settings.get("states", {}).get(user)
    if not state:
        raise SystemExit(f"No state found for user: {user!r}")

    workspaces = state.get("workspaces", {})
    final_workspace = str(state.get("final_workspace", "1"))

    # Only workspaces that have apps
    active = {k: v for k, v in workspaces.items() if v.get("apps")}

    print(f"\n  Wendy — applying state for {user}")
    print(f"  Active workspaces: {list(active.keys())}\n")

    # Step 1: clear only active workspaces to Z
    _move_active_workspaces_to_z(list(active.keys()))

    # Step 2: find music workspace (has music_url)
    music_ws = None
    for ws_id, ws_data in active.items():
        if ws_data.get("music_url", "").strip():
            music_ws = ws_id
            break

    # Step 3: music workspace first
    if music_ws:
        _apply_workspace(music_ws, active[music_ws], settings, cmd_delay)

    # Step 4: remaining workspaces in order (1-9, 0, a-z)
    def _ws_sort_key(k: str) -> tuple:
        if k.isdigit():
            n = int(k)
            return (0, n if n != 0 else 10)
        return (1, k.lower())

    ordered = sorted(
        [k for k in active if k != music_ws],
        key=_ws_sort_key,
    )
    for ws_id in ordered:
        _apply_workspace(ws_id, active[ws_id], settings, cmd_delay)

    # Step 5: go to final workspace
    print(f"\n  → Final workspace: {final_workspace}")
    _run_aerospace(["workspace", final_workspace])

    print("\n  ✓ State applied.\n")


def main() -> None:
    user = sys.argv[1] if len(sys.argv) > 1 else "Tony Stark"
    apply_state(user)


if __name__ == "__main__":
    main()