#!/usr/bin/env python3
"""
Apply Wendy workspace state from config.json (profiles + trigger.target_profiles).
Run by clap_detector / motion / manual:  python3 state_runner.py
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

ROOT = Path(__file__).resolve().parent
CONFIG_PATH = ROOT / "config.json"


def _load_config() -> dict:
    if not CONFIG_PATH.is_file():
        raise SystemExit(f"Missing {CONFIG_PATH.name} at repo root.")
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def _settings(cfg: dict) -> dict:
    s = cfg.get("settings") or {}
    return s if isinstance(s, dict) else {}


def _delay_after_command(cfg: dict) -> float:
    s = _settings(cfg)
    return float(s.get("apply_command_delay_sec", 1.2))


def _delay_pre_arrange(cfg: dict) -> float:
    s = _settings(cfg)
    return float(s.get("apply_pre_arrange_delay_sec", 2.0))


def _youtube_url_with_autoplay(url: str) -> str:
    """Append autoplay=1 for YouTube watch / youtu.be links (helps some browsers)."""
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


def _simulate_space_in_firefox() -> None:
    """Try to start playback (YouTube often focuses play button). Needs Accessibility for Terminal/Python."""
    try:
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Firefox" to activate',
                "-e",
                "delay 1.3",
                "-e",
                'tell application "System Events" to keystroke space',
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (subprocess.TimeoutExpired, OSError):
        pass


def _resolve_profile_ids(cfg: dict) -> list[str]:
    t = cfg.get("trigger") or {}
    if not isinstance(t, dict):
        return ["dev-mode"]
    seq = t.get("target_profiles")
    if isinstance(seq, list) and seq:
        return [str(x) for x in seq]
    one = t.get("target_profile")
    if one:
        return [str(one)]
    return ["dev-mode"]


def _profile_by_id(cfg: dict, pid: str) -> dict | None:
    for p in cfg.get("profiles", []):
        if isinstance(p, dict) and p.get("id") == pid:
            return p
    return None


def _run_aerospace(argv: list[str]) -> int:
    r = subprocess.run(["aerospace", *argv], cwd=str(ROOT))
    return int(r.returncode)


def _run_layout_command(cmd: str) -> bool:
    """
    Run one line from profile layout.commands.

    AeroSpace *config* uses exec-and-forget / exec-and-await — these are NOT
    `aerospace` CLI subcommands. Strip the keyword and run the rest with the OS
    (e.g. open, bash).

    Returns True if a post-command delay should be applied (opens / exec).
    """
    cmd = cmd.strip()
    if not cmd:
        return False
    parts = shlex.split(cmd)
    if not parts:
        return False

    head = parts[0]
    if head in ("exec-and-forget", "exec-and-await"):
        rest = parts[1:]
        if not rest:
            print(f"     ⚠ empty {head}")
            return False
        print(f"     {head}: {' '.join(rest)}")
        if head == "exec-and-forget":
            subprocess.Popen(rest, cwd=str(ROOT), start_new_session=True)
        else:
            subprocess.run(rest, cwd=str(ROOT))
        return True

    print(f"     aerospace {' '.join(parts)}")
    _run_aerospace(parts)
    return False


def _list_windows_bundle_all_monitors(bundle_id: str) -> list:
    out = subprocess.run(
        [
            "aerospace",
            "list-windows",
            "--monitor",
            "all",
            "--app-bundle-id",
            bundle_id,
            "--json",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if out.returncode != 0:
        return []
    try:
        data = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return []
    return data if isinstance(data, list) else []


def _ensure_bundle_on_workspace(
    workspace: str,
    bundle_id: str,
    open_cmd: str,
    cmd_delay: float,
) -> None:
    """
    If the app already has windows on any monitor, move them to `workspace`.
    Otherwise run `open_cmd` (macOS `open`, not aerospace).
    """
    if bundle_id == "com.apple.finder":
        _finder_ensure_on_workspace(workspace, cmd_delay)
        return

    rows = _list_windows_bundle_all_monitors(bundle_id)
    if rows:
        for row in rows:
            wid = row.get("window-id")
            if wid is None:
                continue
            print(
                f"     move window {wid} ({row.get('app-name', '?')}) → workspace {workspace}"
            )
            _run_aerospace(
                ["move-node-to-workspace", "--window-id", str(wid), workspace]
            )
        time.sleep(cmd_delay)
        return

    oc = open_cmd.strip()
    if oc:
        print(f"     open (no window yet): {oc}")
        subprocess.run(shlex.split(oc), cwd=str(ROOT))
        time.sleep(cmd_delay)


def _finder_ensure_on_workspace(workspace: str, cmd_delay: float) -> None:
    """
    Finder rarely shows up usefully via `open -n …/Finder.app`.
    Move any listed Finder windows to `workspace`, then open $HOME so Finder
    gets a normal window and comes forward.
    """
    bid = "com.apple.finder"
    rows = _list_windows_bundle_all_monitors(bid)
    if rows:
        for row in rows:
            wid = row.get("window-id")
            if wid is None:
                continue
            print(
                f"     move window {wid} ({row.get('app-name', '?')}) → workspace {workspace}"
            )
            _run_aerospace(
                ["move-node-to-workspace", "--window-id", str(wid), workspace]
            )
        time.sleep(min(0.5, cmd_delay))

    home = str(Path.home())
    print(f"     Finder: open {home} (normal window + activate)")
    subprocess.Popen(["open", home], cwd=str(ROOT), start_new_session=True)
    time.sleep(cmd_delay)


def _focus_bundle_workspace(workspace: str, bundle_id: str) -> bool:
    """AeroSpace 0.20.x: resolve window via list-windows, then focus --window-id."""
    for _ in range(40):
        out = subprocess.run(
            [
                "aerospace",
                "list-windows",
                "--workspace",
                workspace,
                "--app-bundle-id",
                bundle_id,
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        if out.returncode != 0:
            time.sleep(0.15)
            continue
        try:
            data = json.loads(out.stdout or "[]")
        except json.JSONDecodeError:
            time.sleep(0.15)
            continue
        if not data:
            time.sleep(0.15)
            continue
        wid = data[0].get("window-id")
        if wid is None:
            time.sleep(0.15)
            continue
        _run_aerospace(["focus", "--window-id", str(wid)])
        return True
    return False


def _run_arrange_line(workspace: str, line: str) -> None:
    line = line.strip()
    if not line:
        return
    m = re.match(r"^focus\s+--app-bundle-id\s+(\S+)\s*$", line)
    if m:
        bid = m.group(1)
        if not _focus_bundle_workspace(workspace, bid):
            print(f"  ⚠ arrange: no window for bundle {bid} on ws {workspace}")
        return
    parts = shlex.split(line)
    if parts:
        _run_aerospace(parts)


def _maybe_play_music(profile: dict, cfg: dict) -> bool:
    """
    Optional: local file (afplay) or youtube_url (Firefox).
    Returns True if a YouTube browser tab was opened (caller may settle on workspace).
    """
    music = profile.get("music")
    if not isinstance(music, dict):
        return False
    url = music.get("youtube_url")
    if isinstance(url, str) and url.strip():
        raw = url.strip()
        u = _youtube_url_with_autoplay(raw)
        player = str(music.get("player", "firefox")).lower().strip()
        if player == "mpv" and shutil.which("mpv"):
            print(f"     music: mpv → {u[:72]}{'…' if len(u) > 72 else ''}")
            subprocess.Popen(
                ["mpv", "--really-quiet", "--no-terminal", u],
                cwd=str(ROOT),
                start_new_session=True,
            )
            time.sleep(0.5)
            return False
        print(f"     music: Firefox → {u[:72]}{'…' if len(u) > 72 else ''}")
        subprocess.Popen(
            ["open", "-a", "Firefox", u],
            cwd=str(ROOT),
            start_new_session=True,
        )
        time.sleep(1.0)
        return True
    path = music.get("path")
    if isinstance(path, str) and path.strip() and os.path.isfile(path):
        subprocess.Popen(["afplay", path.strip()], cwd=str(ROOT))
    return False


def _after_youtube_browser(cfg: dict, workspace: str) -> None:
    """Stay on workspace while the tab loads; optional Space to start playback."""
    s = _settings(cfg)
    settle = float(s.get("youtube_settle_sec", 7.0))
    print(f"     (YouTube: wait {settle}s on ws {workspace}, then refocus)")
    time.sleep(settle)
    _run_aerospace(["workspace", workspace])
    time.sleep(0.4)
    if s.get("youtube_simulate_play"):
        print("     (YouTube: simulate Space — grant Accessibility if needed)")
        _simulate_space_in_firefox()


def apply_profiles(cfg: dict, profile_ids: list[str] | None = None) -> None:
    ids = profile_ids if profile_ids is not None else _resolve_profile_ids(cfg)
    cmd_delay = _delay_after_command(cfg)
    arrange_delay = _delay_pre_arrange(cfg)

    print("\n  Wendy — applying state from config.json")
    print(f"  Profiles: {', '.join(ids)}\n")

    for pid in ids:
        prof = _profile_by_id(cfg, pid)
        if not prof:
            print(f"  ✗ Unknown profile id: {pid!r}")
            continue
        name = prof.get("name", pid)
        ws = str(prof.get("workspace", "1"))
        layout = prof.get("layout") or {}
        commands = layout.get("commands") or []
        reloc = layout.get("relocatable_apps") or []
        arrange = layout.get("arrange") or []

        print(f"  ⬤ Profile «{name}» (workspace {ws})")

        for cmd in commands:
            cmd = str(cmd).strip()
            if not cmd:
                continue
            if _run_layout_command(cmd):
                time.sleep(cmd_delay)

        if isinstance(reloc, list) and reloc:
            print(f"     (bring apps into workspace {ws})")
            for entry in reloc:
                if not isinstance(entry, dict):
                    continue
                bid = entry.get("bundle_id")
                if not bid:
                    continue
                open_cmd = str(entry.get("open_cmd", ""))
                _ensure_bundle_on_workspace(ws, str(bid), open_cmd, cmd_delay)

        opened_yt = _maybe_play_music(prof, cfg)
        if opened_yt:
            _after_youtube_browser(cfg, ws)

        if arrange:
            print(f"     (arrange after {arrange_delay:.1f}s)")
            time.sleep(arrange_delay)
            for line in arrange:
                _run_arrange_line(ws, str(line))

        print("")

    print("  ✓ State applied.\n")


def main() -> None:
    cfg = _load_config()
    extra = [x for x in sys.argv[1:] if x.strip()]
    apply_profiles(cfg, extra if extra else None)


if __name__ == "__main__":
    main()
