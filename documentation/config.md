# Wendy — Main config hub (`main.py`)

## Purpose

Entry point for Wendy’s configuration TUI. Runs immediately after the launch color picker (`config/colorpicker.py`), builds the palette from the chosen mode, then acts as a **navigation hub** — routing into each configuration section. Contains no persistence logic itself; submodules use `config/settings_store.py`.

---

## Flow

```
config/colorpicker.py  →  main.py  →  config/apps.py       (returns bool: changed)
                              →  config/colormode.py  (returns bool: changed)
                              →  config/states.py     (returns bool: changed)
```

`pick_color_mode()` runs once at startup. Its return value seeds `color_mode` and `make_palette(color_mode)`. Each submenu receives `stdscr` and the current `color_mode`. After **Apps** or **States**, the hub calls `make_palette(color_mode)` again so the palette stays consistent. After **Color Mode**, if the user changed the setting, `main.py` flips its local `color_mode` and rebuilds the palette.

---

## Related modules

| Module | Role |
|--------|------|
| `main.py` | Hub loop, menu, footer jokes/messages |
| `config/colorpicker.py` | Session-only light/dark choice at launch (`pick_color_mode`) |
| `config/palette.py` | `make_palette(color_mode)` → `RED`, `PINK`, `NORM`, `DIM` |
| `config/settings_store.py` | Path to repo-root `settings.json`, load/save, canonical JSON shape |
| `config/apps.py` | Per-category default apps |
| `config/colormode.py` | Persist `color_mode` in `settings.json` |
| `config/states.py` | Named states (list + placeholder detail) |

---

## What `main.py` stores

No file of its own. Runtime state:

| Variable | Description |
|----------|-------------|
| `color_mode` | From `pick_color_mode()` at launch; updated when **Color Mode** saves a change |
| `message` | Footer text — joke or update confirmation |
| `is_update` | Whether the footer uses the “update” style |

---

## Menu items

Order matches `MENU_ITEMS` in `main.py`:

| Item | Module | Description |
|------|--------|-------------|
| Apps | `config/apps.py` | Default app per category (browser, IDE, music, notes, terminal) |
| Color Mode | `config/colormode.py` | Choose Dark/Light and save to `settings.json` |
| States | `config/states.py` | Named states; detail screen is placeholder |

---

## `settings.json` (via `settings_store`)

Saved at the **repository root** (`REPO_ROOT/settings.json`), not necessarily the current working directory. The config TUI writes a **canonical** document with three top-level keys:

- `color_mode` — `"dark"` or `"light"`
- `apps` — object with keys `browser`, `ide`, `music`, `notes`, `terminal` (string values, `.app` stripped)
- `states` — object mapping state names to objects (currently `{}` per state)

`normalize_settings()` can fold **legacy** top-level keys (`browser`, `ide`, …) into `apps`. See `documentation/apps.md` and `config/settings_store.py` for details.

---

## Visual structure

```
row 0    @ WENDY   config          ↑↓ navigate   enter open   esc quit
row 1   ──────────────────────────────────────────────────────────────
row 2   (empty)
row 3     Apps
row 4   (empty)
row 5     Color Mode
row 6   (empty)
row 7     States
...
row h-2 ──────────────────────────────────────────────────────────────
row h-1  joke or update message
```

---

## Color pairs (`config/palette.py`)

Loaded via `make_palette(color_mode)`. Submodules re-init after returning where needed.

| Alias | Role |
|-------|------|
| `RED` | Brand — wordmark, dividers, selected items (`A_BOLD`; custom color 16 when supported) |
| `PINK` | Controls string, some accents (`A_BOLD`; custom color 17 when supported) |
| `NORM` | Unselected labels |
| `DIM` | `NORM` + `A_DIM` — dimmed text |

If the terminal cannot change colors, custom reds/pinks fall back to `COLOR_RED` / `COLOR_MAGENTA`.

---

## Header (row 0–1)

- `@ WENDY` — `RED`, column 0
- `config` — `DIM`, column 9
- Controls — `PINK`, right-aligned: `w - len(controls) - 1`
- Row 1 — full-width red `ACS_HLINE` via `stdscr.hline()` (not `safe()` — see below)

---

## Menu (row 3+)

- Items start at row 3, spaced every **two** rows
- Selected: `>` at column 2 in `RED`, label at column 4 in `RED`
- Unselected: label at column 4 in `NORM`

---

## Footer (rows h-2 and h-1)

Row `h-2` — full-width red `ACS_HLINE`.

Row `h-1` — message styling:

| State | Format |
|-------|--------|
| Navigating (joke) | ` "…" ` — text in `PINK` |
| After an update | ` … ` — text in `NORM` (no quote characters in the template) |

Jokes rotate on every arrow key in the hub. After **Apps** or **States**, the footer uses the update style only when the submodule returns `True`. After **Color Mode**, `main.py` always uses the update-style footer (no quotes), with either the “switched” or “same as before” message.

### Update messages by action

| Action | Message |
|--------|---------|
| Apps — saved | `App preferences updated.` |
| Apps — no save | new random joke |
| Color Mode — changed | `Switched to {mode} mode. Good choice.` |
| Color Mode — same | `Same as before. No judgment.` |
| States — saved | `States saved.` |
| States — no save | new random joke |

---

## `safe()` helper

Clips text at `(y, x)` and ignores out-of-bounds / curses errors. Used for text, not for `hline` (string slicing breaks box-drawing).

---

## Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor; new joke while navigating |
| `enter` | Open selected section |
| `q` / `esc` | Quit |

---

## Design principles

- **Hub only** — routes to `config/*`; no direct writes to `settings.json` except through submodules.
- **Palette** — refreshed after subflows that can affect colors or terminal state.
- **Honest footer** — update lines match what each submodule reports (with the Color Mode quirk noted above).
