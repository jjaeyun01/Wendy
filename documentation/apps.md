# Wendy — Apps Screen (`apps.py`)

## Purpose

Lets the user assign a default application for each category Wendy knows about. Two-level navigation: first pick a category, then pick an app from a filtered list scanned directly from the filesystem.

---

## Flow

```
config.py  →  apps.py  →  category screen  →  app picker screen
                                                      ↓
                                               save to settings.json
                                                      ↓
                                            return to category screen
```

`run_apps()` is called by `config.py` with `stdscr` and `color_mode`. It returns a `bool` — `True` if the user saved at least one selection, `False` if they exited without changing anything. The caller uses this to decide whether to show an update message or a joke.

---

## What It Stores

Selections are persisted to `settings.json` in the working directory immediately on confirm (no separate save step).

```json
{
  "browser": "Arc",
  "ide": "Cursor",
  "music": "Spotify",
  "notes": "Obsidian",
  "terminal": "iTerm2"
}
```

Keys are lowercase category names. Values are app names with `.app` stripped.

---

## Categories

Alphabetical order — same rule as all Wendy screens.

| Category | Saved key |
|----------|-----------|
| Browser | `browser` |
| IDE | `ide` |
| Music | `music` |
| Notes | `notes` |
| Terminal | `terminal` |

---

## App Discovery

Apps are scanned from four locations at startup, deduplicated, and sorted alphabetically:

| Path | Notes |
|------|-------|
| `/Applications` | User-installed apps |
| `/System/Applications` | macOS system apps |
| `/System/Applications/Utilities` | Terminal, Activity Monitor, etc. |
| `~/Applications` | User-scoped installs |

Only `.app` bundles are included. The `.app` suffix is stripped from display names.

---

## App Filtering

Each category has a keyword list (`CATEGORY_HINTS`). An app is included if its name (lowercased) contains any keyword.

| Category | Keywords |
|----------|----------|
| Browser | chrome, firefox, safari, brave, arc, edge, opera, vivaldi |
| IDE | code, xcode, intellij, pycharm, webstorm, goland, rider, clion, rubymine, sublime, atom, zed, cursor, nova |
| Music | spotify, music, itunes, vox, doppler, capo, swinsian, deezer, tidal + all Browser keywords |
| Notes | obsidian, notion, bear, notes, craft, roam, logseq, evernote, simplenote, ulysses, typora |
| Terminal | terminal, iterm, iterm2, warp, alacritty, kitty, hyper, ghostty |

Music intentionally includes all Browser keywords — the user listens to music through a browser.

If no apps match, the full unfiltered list is shown so the user is never stuck.

---

## Visual Structure

### Category screen

```
row 0   @ WENDY   apps          ↑↓ navigate   enter select   esc back
row 1   ──────────────────────────────────────────────────────────────
row 2   (empty)
row 3   > Browser   Arc               ← selected (red) + current value (dim)
row 4   (empty)
row 5     IDE                         ← unselected (NORM)
row 6   (empty)
row 7     Music
row 8   (empty)
row 9     Notes
row 10  (empty)
row 11    Terminal
```

### App picker screen

```
row 0   @ WENDY   apps  /  browser   ↑↓ navigate   enter select   esc back
row 1   ──────────────────────────────────────────────────────────────
row 2   (empty)
row 3   > Arc                         ← selected (red)
row 4   (empty)
row 5     Brave Browser               ← unselected (NORM)
row 6   (empty)
row 7     Firefox
...
```

---

## Color Pairs

Apps uses its own pair assignments (1–3 only). `config.py` re-initializes its own pairs after `run_apps()` returns.

| Pair | Alias | Dark mode | Light mode | Attribute |
|------|-------|-----------|------------|-----------|
| 1 | `RED` | RED on default | RED on default | `A_BOLD` |
| 2 | `NORM` | WHITE on default | BLACK on default | — |
| 2 | `DIM` | WHITE on default | BLACK on default | `A_DIM` |
| 3 | `HINT` | MAGENTA on default | MAGENTA on default | — |

`RED` — brand color, wordmark, dividers, selected items. `HINT` (magenta) — controls string, matches config. `DIM` — current app value shown next to category name.

---

## Header (shared via `draw_header()`)

Both screens share one `draw_header(title)` function. Title changes between screens:

| Screen | Title |
|--------|-------|
| Category | `apps` |
| App picker | `apps  /  {category}` |

Structure:
- `@ WENDY` — `RED`, column 0
- title — `NORM`, column 9
- controls — `HINT`, right-aligned
- row 1 — full-width red `ACS_HLINE` via `stdscr.hline()`

---

## Menu Spacing

Both screens use 2-row spacing between items (one blank row between each). This matches `config.py` and is the standard for all Wendy list screens.

Category screen: `row = 3 + i * 2`
App picker: `row = 3 + screen_i * 2`

The app picker also implements scrolling — `list_rows = (h - 4) // 2` accounts for the doubled spacing when calculating how many items fit.

---

## Scrolling

The app picker scrolls when the list exceeds the visible area:

```python
if app_cursor < scroll:
    scroll = app_cursor
elif app_cursor >= scroll + list_rows:
    scroll = app_cursor - list_rows + 1
```

Cursor always stays visible. No scroll indicators are shown — the list simply moves.

---

## Selected Item Display (Category Screen)

When a category already has a saved app, it is shown dimmed next to the label:

```
> Browser   Arc
```

- Category label: `RED` (selected) or `NORM` (unselected)
- Current value: `DIM` always, regardless of selection state

---

## Return Value

`run_apps()` returns `bool`:

- `True` — user selected and confirmed at least one app (enter was pressed in the app picker)
- `False` — user exited via `q` or `esc` without saving anything

`config.py` uses this to show either `"App preferences updated."` or a new joke.

---

## Navigation

### Category screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor |
| `enter` | Open app picker for selected category |
| `q` / `esc` | Return to config |

### App picker screen

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor, scroll list |
| `enter` | Save selection, return to category screen |
| `q` / `esc` | Return to category screen without saving |

---

## Design Principles

- **Two-level, not flat.** Category → app. Never dumps a combined list of all apps for all categories.
- **Filtered by default, never blocked.** If no apps match a category's keywords, the full list is shown.
- **Immediate persistence.** Saves on confirm, no explicit save step.
- **Honest return.** Returns `True` only if something was actually saved. Callers should not assume a save occurred.
- **Shared header.** `draw_header()` is the pattern for sub-screens — one function, title string changes per level.
- **No footer bar.** Only `config.py` has the Wendy message footer. Sub-screens are clean.
