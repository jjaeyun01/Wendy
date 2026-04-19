"""
settings_bridge.py — Converts archive/settings.json → config.json at trigger time.

Flow:
  1. User configures apps + states in terminal TUI (writes archive/settings.json)
  2. Double-clap fires state_runner.py
  3. state_runner.py calls settings_bridge.sync() first
  4. sync() reads settings.json and overwrites relevant config.json fields
  5. state_runner.py reads the freshly-updated config.json

What gets synced:
  - dev-mode  : IDE app, terminal app (bundle IDs + open commands)
  - jarvis-mode: YouTube URL from the first workspace with a music_url
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

ROOT          = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "archive" / "settings.json"
CONFIG_PATH   = ROOT / "config.json"


# ── App lookup helpers ────────────────────────────────────────────────────────

_SEARCH_DIRS = [
    "/Applications",
    "/System/Applications",
    "/System/Applications/Utilities",
    os.path.expanduser("~/Applications"),
]

# Apps that don't live in /Applications or need a special open command
_SPECIAL_OPEN = {
    "Terminal":    "open -n /System/Applications/Utilities/Terminal.app",
    "Finder":      "open -a Finder",
    "Safari":      "open -n /Applications/Safari.app",
    "Mail":        "open -n /System/Applications/Mail.app",
    "Calendar":    "open -n /System/Applications/Calendar.app",
    "Notes":       "open -n /System/Applications/Notes.app",
    "Music":       "open -n /System/Applications/Music.app",
}


def find_app_path(name: str) -> str | None:
    """Return the .app path for the given app name, or None if not found."""
    for d in _SEARCH_DIRS:
        p = os.path.join(d, f"{name}.app")
        if os.path.exists(p):
            return p
    return None


def get_bundle_id(app_name: str) -> str | None:
    """Return the macOS bundle ID for an installed app using mdls."""
    path = find_app_path(app_name)
    if not path:
        return None
    try:
        r = subprocess.run(
            ["mdls", "-name", "kMDItemCFBundleIdentifier", "-r", path],
            capture_output=True, text=True, timeout=4,
        )
        bid = r.stdout.strip()
        return bid if bid and bid != "(null)" else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def make_open_cmd(app_name: str) -> str:
    """Return a shell open command for the given app."""
    if app_name in _SPECIAL_OPEN:
        return _SPECIAL_OPEN[app_name]
    path = find_app_path(app_name)
    if path:
        return f"open -n \"{path}\""
    return f"open -a \"{app_name}\""


# ── AeroSpace arrange helpers ─────────────────────────────────────────────────
# Maps (n_apps, layout_id) → function(slot_order: list[bundle_id]) → list[str]
# slot_order follows the slot letters A, B, C, D from settings.json.

def _arrange_2_side_by_side(bids: list[str]) -> list[str]:
    """A | B"""
    a, b = bids
    return [
        f"focus --app-bundle-id {a}", "layout h_tiles",
        f"focus --app-bundle-id {b}", "join-with right",
    ]


def _arrange_2_stacked(bids: list[str]) -> list[str]:
    """A / B"""
    a, b = bids
    return [
        f"focus --app-bundle-id {a}", "layout v_tiles",
        f"focus --app-bundle-id {b}", "join-with down",
    ]


def _arrange_3_thirds(bids: list[str]) -> list[str]:
    """A | B | C"""
    a, b, c = bids
    return [
        f"focus --app-bundle-id {a}", "layout h_tiles",
        f"focus --app-bundle-id {b}", "join-with right",
        f"focus --app-bundle-id {c}", "join-with right",
    ]


def _arrange_3_side_stacked(bids: list[str]) -> list[str]:
    """A (left) | B (top-right) / C (bottom-right)"""
    a, b, c = bids
    return [
        f"focus --app-bundle-id {a}", "layout h_tiles",
        f"focus --app-bundle-id {b}", "join-with right",
        f"focus --app-bundle-id {c}", "join-with down",
    ]


def _arrange_3_stacked_side(bids: list[str]) -> list[str]:
    """B (top-left) / C (bottom-left) | A (right)"""
    a, b, c = bids
    return [
        f"focus --app-bundle-id {b}", "layout h_tiles",
        f"focus --app-bundle-id {c}", "join-with down",
        f"focus --app-bundle-id {a}", "join-with right",
    ]


def _arrange_4_grid(bids: list[str]) -> list[str]:
    """A B / C D (2×2)"""
    a, b, c, d = bids
    return [
        f"focus --app-bundle-id {a}", "layout h_tiles",
        f"focus --app-bundle-id {b}", "join-with right",
        f"focus --app-bundle-id {c}", "join-with down",  # below A
        f"focus --app-bundle-id {d}", "join-with down",  # below B (approximate)
    ]


_ARRANGE_FN = {
    (2, 1): _arrange_2_side_by_side,
    (2, 2): _arrange_2_stacked,
    (3, 1): _arrange_3_thirds,
    (3, 2): _arrange_3_side_stacked,
    (3, 3): _arrange_3_stacked_side,
    (4, 1): _arrange_4_grid,
}


# ── settings.json → config.json ───────────────────────────────────────────────

def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _active_state(settings: dict) -> dict | None:
    """Return the first (or marked active) state from settings.json."""
    states = settings.get("states", {})
    if not states:
        return None
    active_name = settings.get("active_state")
    if active_name and active_name in states:
        return states[active_name]
    return next(iter(states.values()))


def _build_relocatable(role: str, app_name: str, _warned: set | None = None) -> dict | None:
    """Build a relocatable_apps entry for the given app."""
    if not app_name:
        return None

    bid = get_bundle_id(app_name)
    if not bid:
        if _warned is None or app_name not in _warned:
            print(f"  ⚠  settings_bridge: bundle ID not found for «{app_name}» ({role}) — skipped")
            if _warned is not None:
                _warned.add(app_name)
        return None

    return {
        "bundle_id": bid,
        "open_cmd":  make_open_cmd(app_name),
    }


def _workspace_to_profile(
    ws_num: str,
    ws_cfg: dict,
    apps_map: dict[str, str],
    _warned: set | None = None,
) -> dict | None:
    """
    Convert one workspace entry from settings.json into a config.json profile.
    Returns None if the workspace has no apps.
    """
    role_list = ws_cfg.get("apps", [])
    if not role_list:
        return None

    music_url  = ws_cfg.get("music_url", "") or ""
    browser_url = ws_cfg.get("browser_url", "") or ""

    # Build relocatable apps
    reloc = []
    role_to_bid: dict[str, str] = {}
    for role in role_list:
        app_name = apps_map.get(role, "")
        if not app_name:
            continue
        entry = _build_relocatable(role, app_name, _warned)
        if entry:
            reloc.append(entry)
            role_to_bid[role] = entry["bundle_id"]

    # Build arrange commands from layout definition
    layout_def = ws_cfg.get("layout")
    arrange: list[str] = []
    if layout_def and role_to_bid:
        n   = int(layout_def.get("n", len(role_list)))
        lid = int(layout_def.get("id", 1))
        slots: dict[str, str] = layout_def.get("slots", {})

        # Build ordered list of bundle IDs following slot letters A, B, C, D
        slot_order = ["A", "B", "C", "D"][:n]
        bid_order  = []
        for letter in slot_order:
            role = slots.get(letter)
            bid  = role_to_bid.get(role) if role else None
            if bid:
                bid_order.append(bid)

        if len(bid_order) == n:
            fn = _ARRANGE_FN.get((n, lid))
            if fn:
                arrange = fn(bid_order)

    # Music / browser URL extras go to profile-level music block
    profile: dict = {
        "id":        f"ws-{ws_num}",
        "name":      f"workspace {ws_num}",
        "workspace": str(ws_num),
        "layout": {
            "description": f"workspace {ws_num}: {', '.join(role_list)}",
            "commands":    [f"workspace {ws_num}"],
            "relocatable_apps": reloc,
            "arrange":     arrange,
        },
    }

    if music_url:
        profile["music"] = {
            "youtube_url": music_url,
            "player":      apps_map.get("music", "firefox").lower(),
        }

    if browser_url and "browser" in role_to_bid:
        profile["browser_launch"] = {
            "url":    browser_url,
            "app":    apps_map.get("browser", "Firefox"),
        }

    return profile


def _ws_sort_key(ws_num: str, ws_cfg: dict) -> tuple:
    """
    Execution order:
      0순위 — music workspaces first
      1순위 — alphabetic IDs: Z → A
      2순위 — numeric IDs: 9 → 1
    Within each music/non-music group, letters come before numbers.
    """
    has_music = 0 if str(ws_cfg.get("music_url", "")).strip() else 1
    ws_id = str(ws_num).upper()
    is_alpha = ws_id.isalpha()
    type_key = 0 if is_alpha else 1          # letters before numbers
    order_key = -ord(ws_id) if is_alpha else -int(ws_id)
    return (has_music, type_key, order_key)


def build_profiles_from_settings(settings: dict) -> list[dict]:
    """Generate config.json profiles list from settings.json."""
    apps_map = {k.lower(): v for k, v in settings.get("apps", {}).items()}
    state    = _active_state(settings)
    if not state:
        return []

    workspaces = state.get("workspaces", {})
    sorted_items = sorted(workspaces.items(), key=lambda kv: _ws_sort_key(kv[0], kv[1]))

    warned: set = set()
    profiles = []
    for ws_num, ws_cfg in sorted_items:
        p = _workspace_to_profile(str(ws_num), ws_cfg, apps_map, warned)
        if p:
            profiles.append(p)

    return profiles


def sync() -> bool:
    """
    Read archive/settings.json, generate profiles, and update config.json.
    Returns True if config.json was modified.
    """
    if not SETTINGS_PATH.is_file():
        print(f"  ⚠  settings_bridge: {SETTINGS_PATH} not found — using existing config.json")
        return False

    try:
        settings = _load_json(SETTINGS_PATH)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  ⚠  settings_bridge: could not read settings.json: {exc}")
        return False

    new_profiles = build_profiles_from_settings(settings)
    if not new_profiles:
        print("  ⚠  settings_bridge: no workspaces found in settings.json — keeping current config")
        return False

    try:
        config = _load_json(CONFIG_PATH)
    except (json.JSONDecodeError, OSError):
        config = {"version": "1.0.0", "settings": {}, "trigger": {}}

    config["profiles"] = new_profiles

    # Execution order is already sorted by build_profiles_from_settings:
    # music first → Z→A → 9→1
    config["trigger"] = {
        "type": "double_clap",
        "target_profiles": [p["id"] for p in new_profiles],
    }

    _save_json(CONFIG_PATH, config)
    names = [p["name"] for p in new_profiles]
    print(f"  ✓  settings_bridge: config.json updated from settings.json → {names}")
    return True


if __name__ == "__main__":
    sync()
