"""Single source of truth for settings.json path, shape, and persistence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = REPO_ROOT / "settings.json"

# Keys written under "apps" (lowercase in JSON).
APP_KEYS = ("browser", "ide", "music", "notes", "terminal")


def _empty_apps() -> dict[str, str]:
    return {k: "" for k in APP_KEYS}


def normalize_settings(raw: dict[str, Any]) -> dict[str, Any]:
    """Merge legacy top-level keys and old list-shaped `apps` into the canonical shape."""
    out: dict[str, Any] = {
        "color_mode": str(raw.get("color_mode") or "dark"),
        "apps": _empty_apps(),
        "states": dict(raw.get("states") or {}),
    }

    apps = raw.get("apps")
    if isinstance(apps, dict):
        for k in APP_KEYS:
            v = apps.get(k)
            if isinstance(v, str) and v.strip():
                out["apps"][k] = v.strip()
    # Legacy: browser / ide / … as top-level strings
    for key in APP_KEYS:
        v = raw.get(key)
        if isinstance(v, str) and v.strip() and not out["apps"].get(key):
            out["apps"][key] = v.strip()

    return out


def load_settings() -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        return normalize_settings({})
    try:
        raw = json.loads(SETTINGS_PATH.read_text())
    except Exception:
        return normalize_settings({})
    if not isinstance(raw, dict):
        return normalize_settings({})
    return normalize_settings(raw)


def save_settings(settings: dict[str, Any]) -> None:
    """Write only color_mode, apps, and states (canonical settings.json)."""
    merged = normalize_settings(settings)
    payload = {
        "color_mode": merged["color_mode"],
        "apps": {k: merged["apps"].get(k, "") for k in APP_KEYS},
        "states": merged["states"],
    }
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2) + "\n")
