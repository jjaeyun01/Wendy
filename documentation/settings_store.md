# Wendy — Settings persistence (`config/settings_store.py`)

**Code conventions (paths, constants, `save_settings` newline, typing):** `documentation/config-style.md` → **`settings_store.py`**.

## Purpose

Single module for **`settings.json`** path, **normalization**, and **read/write** used by `config/apps.py`, `config/states.py`, and `config/colormode.py`.

## Path

`SETTINGS_PATH` = **`REPO_ROOT / "settings.json"`** (`REPO_ROOT` = parent of `config/`). Independent of shell cwd.

## Canonical JSON (written by `save_settings`)

| Key | Type | Notes |
|-----|------|--------|
| `color_mode` | string | `"dark"` \| `"light"` (default `"dark"` if missing) |
| `apps` | object | Keys: `browser`, `ide`, `music`, `notes`, `terminal` (strings, may be empty) |
| `states` | object | State name → `{ "workspaces": { … } }` — see `documentation/states.md` |

## `normalize_settings(raw)`

- Ensures every **`APP_KEYS`** slot exists under **`apps`**; fills from nested **`apps`** or legacy **top-level** `browser`, `ide`, …
- Ignores legacy **`apps`** when it was a **list**.
- **`states`** defaults to `{}`.

## `load_settings()` / `save_settings()`

- **Load** — parse JSON, return normalized dict; on error or missing file, return defaults.
- **Save** — merge through `normalize_settings`, then write **only** the three canonical keys (no passthrough extras like `youtube_url`).

## Principles

- One file, one shape for the TUI.
- Repo-root path for predictable tooling.
