"""Single source of truth for settings.json path, shape, and persistence."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_PATH = REPO_ROOT / "settings.json"
LAYOUT_CATALOG_DEFAULTS_PATH = REPO_ROOT / "layout_catalog.defaults.json"

# Keys written under "apps" (lowercase in JSON).
APP_KEYS = ("browser", "ide", "music", "notes", "terminal")


def _empty_apps() -> dict[str, Any]:
    return {k: {"name": "", "bundle_id": ""} for k in APP_KEYS}


def _normalize_app_value(v: Any) -> dict[str, str]:
    """Coerce a legacy string or existing dict into canonical {name, bundle_id} shape."""
    if isinstance(v, dict):
        return {
            "name": str(v.get("name") or "").strip(),
            "bundle_id": str(v.get("bundle_id") or "").strip(),
        }
    if isinstance(v, str) and v.strip():
        return {"name": v.strip(), "bundle_id": ""}
    return {"name": "", "bundle_id": ""}


def _layout_catalog_defaults() -> dict[str, Any]:
    """Fallback when settings.json has no layout_catalog (repo ships layout_catalog.defaults.json)."""
    if not LAYOUT_CATALOG_DEFAULTS_PATH.is_file():
        return {}
    try:
        raw = json.loads(LAYOUT_CATALOG_DEFAULTS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return raw if isinstance(raw, dict) else {}


def normalize_settings(raw: dict[str, Any]) -> dict[str, Any]:
    """Merge legacy top-level keys and old list-shaped `apps` into the canonical shape."""
    out: dict[str, Any] = {
        "color_mode": str(raw.get("color_mode") or "dark"),
        "apps": _empty_apps(),
        "states": dict(raw.get("states") or {}),
    }

    lc = raw.get("layout_catalog")
    if isinstance(lc, dict) and lc:
        out["layout_catalog"] = lc
    else:
        out["layout_catalog"] = _layout_catalog_defaults()

    apps = raw.get("apps")
    if isinstance(apps, dict):
        for k in APP_KEYS:
            v = apps.get(k)
            normalized = _normalize_app_value(v)
            if normalized["name"]:
                out["apps"][k] = normalized

    # Legacy: browser / ide / … as top-level strings
    for key in APP_KEYS:
        v = raw.get(key)
        if v and not out["apps"].get(key, {}).get("name"):
            normalized = _normalize_app_value(v)
            if normalized["name"]:
                out["apps"][key] = normalized

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
    """Write color_mode, apps, states, and layout_catalog (canonical settings.json)."""
    merged = normalize_settings(settings)

    lc = merged.get("layout_catalog")
    if not isinstance(lc, dict) or not lc:
        lc = _layout_catalog_defaults()

    payload = {
        "color_mode": merged["color_mode"],
        "apps": {k: merged["apps"].get(k, {"name": "", "bundle_id": ""}) for k in APP_KEYS},
        "states": merged["states"],
        "layout_catalog": lc,
    }
    SETTINGS_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
