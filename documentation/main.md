# Wendy — Main hub (`main.py`)

**Shared UI/code conventions:** `documentation/config-style.md` (hub layout, footer rules, `safe`, keys, palette).

## Purpose

Configuration TUI entry after the launch picker (`config/colorpicker.py`). Builds the palette from `pick_color_mode()`, then **routes** to `config/apps.py`, `config/colormode.py`, and `config/states.py`. Does not read or write `settings.json` itself — submodules use `config/settings_store.py`.

## Flow

```
config/colorpicker.py  →  main.py  →  config/apps.py       (bool: changed)
                              →  config/colormode.py  (bool: changed)
                              →  config/states.py     (bool: changed)
```

`pick_color_mode()` runs once; its return seeds `color_mode` and `make_palette(color_mode)`. After **Apps** or **States**, the hub refreshes the palette. After **Color Mode**, if the user saved a different mode, `main.py` updates local `color_mode` and rebuilds the palette.

## Related modules

| Module | Role |
|--------|------|
| `main.py` | Hub loop, `MENU_ITEMS`, jokes, footer messages |
| `config/colorpicker.py` | Session-only light/dark at launch |
| `config/palette.py` | `make_palette` — see **Palette** in `config-style.md` |
| `config/settings_store.py` | Repo-root `settings.json` |
| `config/apps.py` | Default app per global category |
| `config/colormode.py` | Persist `color_mode` |
| `config/states.py` | Named states → workspaces → per-workspace apps/URLs (`documentation/states.md`) |

## Runtime state (`main.py` only)

| Variable | Role |
|----------|------|
| `color_mode` | From `pick_color_mode()`; updated when **Color Mode** saves |
| `message` | Footer text |
| `is_update` | Whether the footer uses update-style vs joke-style |

## Menu

Order is `MENU_ITEMS`: **Apps**, **Color Mode**, **States**.

## `settings.json` overview

Written by the TUI via `settings_store` (repo root). Top-level keys:

- `color_mode` — `"dark"` | `"light"`
- `apps` — `browser`, `ide`, `music`, `notes`, `terminal`
- `states` — nested structure in `documentation/states.md`

Legacy top-level keys can be folded into `apps` by `normalize_settings` — see `documentation/settings_store.md` and `documentation/apps.md`.

## Hub footer messages

Exact strings and when they appear are defined in **Global — `main.py` hub** → `documentation/config-style.md`.

## Principles

- **Hub only** — no direct `settings.json` access; delegate to `config/*`.
- **Palette** — refresh after subflows that can affect colors or the terminal.
