# Wendy — Apps screen (`config/apps.py`)

## Purpose

Lets the user assign a default application for each category. Two-level navigation: pick a category, then pick an app from a list filtered from `.app` bundles on disk. Persistence goes through `config/settings_store.py` into the repo-root `settings.json`.

---

## Flow

```
main.py  →  run_apps()  →  category screen  →  app picker screen
                                                      ↓
                                               save via settings_store
                                                      ↓
                                            return to category screen
```

`run_apps(stdscr, color_mode)` is imported from `main.py`. It returns `True` if the user confirmed at least one app selection, `False` if they left without saving (e.g. only `esc`/`q`).

---

## What it stores

Selections are merged into **`settings.json`** under the nested **`apps`** object. Keys are lowercase category names. Values are app display names with `.app` stripped.

Example (canonical file also has `color_mode` and `states` at the top level):

```json
{
  "color_mode": "dark",
  "apps": {
    "browser": "Firefox",
    "ide": "Cursor",
    "music": "Spotify",
    "notes": "Obsidian",
    "terminal": "Ghostty"
  },
  "states": {}
}
```

`save_settings()` rewrites the file using the canonical shape (see `config/settings_store.py`).

---

## Categories

Order matches `CATEGORIES` in code (Browser → IDE → Music → Notes → Terminal).

| Category | Saved key under `apps` |
|----------|-------------------------|
| Browser | `browser` |
| IDE | `ide` |
| Music | `music` |
| Notes | `notes` |
| Terminal | `terminal` |

---

## App discovery

Apps are collected from:

| Path | Notes |
|------|-------|
| `/Applications` | User-installed apps |
| `/System/Applications` | macOS system apps |
| `/System/Applications/Utilities` | Terminal, Activity Monitor, etc. |
| `~/Applications` | User-scoped installs |

Only `.app` bundles are included; the `.app` suffix is stripped from names. Results are deduplicated and sorted case-insensitively.

---

## App filtering (`CATEGORY_HINTS`)

An app is included if its lowercased name contains any hint string for that category.

| Category | Hint keywords (representative) |
|----------|--------------------------------|
| Browser | chrome, firefox, safari, brave, arc, edge, opera, vivaldi |
| IDE | code, xcode, intellij, pycharm, …, cursor, nova |
| Music | spotify, music, itunes, …, plus the same browser-related hints as Browser |
| Notes | obsidian, notion, bear, notes, craft, roam, logseq, … |
| Terminal | terminal, iterm, iterm2, warp, alacritty, kitty, hyper, ghostty |

If nothing matches, the **full** app list is shown so the user is never stuck.

---

## Visual structure

### Category screen

```
row 0   @ WENDY   apps          ↑↓ navigate   enter select   esc back
row 1   ──────────────────────────────────────────────────────────────
row 3   > Browser   Firefox
...
```

### App picker screen

Header title: `apps  /  {category}` with the category in **lowercase** (e.g. `browser`).

---

## Color / palette

Uses `make_palette(color_mode)` from `config/palette.py` — **`RED`**, **`PINK`**, **`NORM`**, **`DIM`** (no separate `HINT` symbol). Controls string uses **`PINK`**; current value next to the category uses **`DIM`**.

---

## Header (`draw_header`)

- `@ WENDY` — `RED`
- Title — `DIM`
- Controls — `PINK`, right-aligned
- Row 1 — red `ACS_HLINE`

---

## Scrolling (app picker)

Same pattern as other list screens: `list_rows = (h - 4) // 2`, cursor-centered scrolling via `scroll` index.

---

## Return value

- `True` — at least one selection was saved from the app picker (`enter` with a non-empty filtered list).
- `False` — exited without saving.

---

## Navigation

### Category screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor |
| `enter` | Open app picker |
| `q` / `esc` | Back to hub |

### App picker

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor / scroll |
| `enter` | Save and return to categories |
| `q` / `esc` | Return without saving |

---

## Design principles

- **Two-level UX** — category first, then app.
- **Immediate save** on confirm in the picker.
- **Filtered by default**, full list as fallback.
