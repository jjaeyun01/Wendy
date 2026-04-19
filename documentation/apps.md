# Wendy — Apps (`config/apps.py`)

**Code layout, `safe`, `draw_header`, list spacing, keys:** `documentation/config-style.md`.

## Purpose

Two-level flow: pick a **category** (Browser, IDE, Music, Notes, Terminal), then pick an **app** from `.app` bundles on disk. Saves into `settings.json` → **`apps`** via `config/settings_store.py`.

## Flow

```
main.py  →  run_apps()  →  category list  →  app picker  →  save  →  category list
```

`run_apps(stdscr, color_mode) -> bool`: **`True`** if the user saved at least one pick; **`False`** if they exited without saving.

## Stored data

Nested under **`apps`**; keys are lowercase category names; values are `.app` names without the suffix.

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

Full file shape: `documentation/settings_store.md`.

## Categories

Order matches `CATEGORIES` in code.

| Category | Key |
|----------|-----|
| Browser | `browser` |
| IDE | `ide` |
| Music | `music` |
| Notes | `notes` |
| Terminal | `terminal` |

## App discovery

Scans: `/Applications`, `/System/Applications`, `/System/Applications/Utilities`, `~/Applications`. Only `*.app`; dedupe; sort case-insensitively.

## Filtering (`CATEGORY_HINTS`)

Include an app if its lowercased name contains any hint for that category. **Music** includes the same browser-related hints as Browser (listening in a browser). If nothing matches, show the **full** list.

## Picker header

Second-level title: `apps  /  {category}` with **lowercase** category (e.g. `browser`).

## Navigation (apps-specific)

| Screen | `↑` `↓` | `enter` | `q` / `esc` |
|--------|---------|---------|-------------|
| Categories | move | open picker | back to hub |
| App picker | move / scroll | save & return | return without save |

## Principles

- Category first, then app.
- Save on confirm in the picker.
- Prefer filtered list; never block on an empty filter result.
