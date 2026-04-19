# Wendy — Settings persistence (`config/settings_store.py`)

## Purpose

Single place for **`settings.json`** location, **normalization** of legacy shapes, and **read/write** used by `config/apps.py`, `config/states.py`, and `config/colormode.py`.

---

## Path

`SETTINGS_PATH` = **`REPO_ROOT / "settings.json"`**, where `REPO_ROOT` is the parent of the `config/` package (the Wendy project root). This does not depend on the shell’s current working directory.

---

## Canonical JSON shape

Written by `save_settings()`:

| Key | Type | Notes |
|-----|------|--------|
| `color_mode` | string | `"dark"` or `"light"` (default `"dark"` if missing) |
| `apps` | object | Keys exactly: `browser`, `ide`, `music`, `notes`, `terminal` — string values (may be empty) |
| `states` | object | Map of state name → object (often `{}`) |

---

## `normalize_settings(raw)`

- Ensures `apps` has every `APP_KEYS` entry; fills from nested `apps` dict or from **legacy** top-level `browser`, `ide`, etc.
- Ignores legacy `apps` when it was a **list** (old format).
- `states` defaults to `{}`.

---

## `load_settings()` / `save_settings()`

- **Load** — parses JSON, returns normalized dict; on error or missing file, returns defaults.
- **Save** — merges through `normalize_settings`, then writes **only** the three canonical keys (no extra keys like `youtube_url`).

---

## Design principles

- **One file, one shape** — avoid drift between modules.
- **Repo-root file** — predictable location for scripts and the TUI.
