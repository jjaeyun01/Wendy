# Wendy — Config Hub (`config.py`)

## Purpose

The main entry point for Wendy's configuration. Launches immediately after the color picker and acts purely as a navigation hub — routing the user into each configuration section. Contains no configuration logic itself.

---

## Flow

```
colorpicker.py  →  config.py  →  apps.py         (returns bool: changed)
                            →  states.py       (stub)
                            →  colorpicker.py  (re-enterable)
```

`config.py` calls `pick_color_mode()` first, receives the result, initializes its color pairs, then drops into the menu loop. When the user selects a section, the relevant module is called with `stdscr` and `color_mode`. When that module exits, config **reinitializes its own color pairs** before resuming — this prevents sub-modules from corrupting the palette.

---

## What It Stores

No persistent data. Two runtime values held in memory:

| Variable | Description |
|----------|-------------|
| `color_mode` | Carried in from `colorpicker.py`, passed into every sub-module |
| `message` | Current footer text — either a joke or an update confirmation |

---

## Menu Items

Alphabetical order — this is the standard for all Wendy screens.

| Item | Module | Description |
|------|--------|-------------|
| Apps | `apps.py` | Assign default apps per category |
| Color Mode | `colorpicker.py` | Re-run the color picker to switch light / dark mid-session |
| States | `states.py` | Manage named workspace launch configurations |

---

## Visual Structure

```
row 0    @ WENDY   config          ↑↓ navigate   enter open   esc quit
row 1   ──────────────────────────────────────────────────────────────
row 2   (empty)
row 3   > Apps
row 4   (empty)
row 5     Color Mode
row 6   (empty)
row 7     States
...
row h-2 ──────────────────────────────────────────────────────────────
row h-1  "joke or update message"
```

---

## Color Pairs

Initialized once on entry, and **re-initialized after returning from any sub-module** to prevent palette corruption.

| Pair | Alias | Dark mode | Light mode | Attribute |
|------|-------|-----------|------------|-----------|
| 1 | `RED` | RED on default | RED on default | `A_BOLD` |
| 2 | `CYAN` | CYAN on default | BLUE on default | `A_BOLD` |
| 3 | `NORM` | WHITE on default | BLACK on default | — |
| 4 | `LABEL` | YELLOW on default | BLACK on default | `A_BOLD` (light) / none (dark) |
| 5 | `GREEN` | GREEN on default | GREEN on default | `A_BOLD` |
| 6 | `HINT` | MAGENTA on default | MAGENTA on default | — |

`RED` is the brand color — used for the wordmark, dividers, and selected items. `HINT` (magenta) is used for the controls string and footer jokes. `NORM` is used for unselected items and the screen title.

---

## Header (row 0–1)

- `@ WENDY` — `RED`, column 0
- `config` — `NORM`, column 9
- controls string — `HINT`, right-aligned: `w - len(controls) - 1`
- row 1 — full-width red `ACS_HLINE` via `stdscr.hline()` (never `safe()` — see below)

---

## Menu (row 3+)

- Items start at row 3, spaced 2 rows apart
- Selected: `>` at column 2 in `RED`, label at column 4 in `RED`
- Unselected: label at column 4 in `NORM`, no arrow

---

## Footer (rows h-2 and h-1)

Row `h-2` — full-width red `ACS_HLINE`.
Row `h-1` — Wendy's message, two modes:

| State | Format | Style |
|-------|--------|-------|
| Navigating | `"joke text"` | `HINT \| A_ITALIC` |
| After a change | `update text` | `NORM` — no quotes, no italic |

Joke rotates on every arrow key press. Update message is set explicitly after a sub-module returns and only shown if something actually changed — otherwise falls back to a new joke.

### Update messages by action

| Action | Message |
|--------|---------|
| Apps — something saved | `App preferences updated.` |
| Apps — nothing saved | new random joke |
| Color Mode — changed | `Switched to {mode} mode. Good choice.` |
| Color Mode — same | `Same as before. No judgment.` |
| States | `States saved.` |

---

## `safe()` Helper

Writes clipped text at `(y, x)`. Silently swallows out-of-bounds and curses errors. Used for all text rendering **except `hline` calls** — `safe()` slices strings by character count which breaks multi-byte Unicode box-drawing characters. Always use `stdscr.hline()` directly for dividers.

---

## Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor, rotate joke |
| `enter` | Open selected section |
| `q` | Quit |

---

## Design Principles

- **Hub, not a form.** Contains zero configuration logic — only routes.
- **Color is always restored.** Every sub-module call is followed by a full color pair re-init.
- **Honest footer.** Update messages only appear if something actually changed.
- **Alphabetical always.** All menu lists in Wendy are alphabetical. New screens must follow this.
- **Modular by design.** Adding a section = one `MENU_ITEMS` entry + one module file. Nothing else changes.
