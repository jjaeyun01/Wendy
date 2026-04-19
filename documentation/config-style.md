# Style guidelines — `config/` Python modules

These rules describe how Wendy’s `config` package is written today. New code should follow them; refactors should converge toward them when touched.

---

## Scope

| File | Role |
|------|------|
| `settings_store.py` | JSON path, load/save, normalization — **no curses** |
| `palette.py` | `make_palette(color_mode)` — shared terminal colors |
| `colorpicker.py` | Launch-only light/dark UI — **does not** use `palette` or `settings_store` |
| `apps.py`, `states.py`, `colormode.py` | Full-screen flows: `make_palette` + optional `settings_store` |

---

## Imports

1. **Standard library** — `curses`, `json`, `os`, `pathlib`, `random`, `typing` as needed.
2. **Blank line.**
3. **Package imports** — `from config.…` (always absolute from project root when running `main.py`).

`settings_store.py` may use `from __future__ import annotations` and `typing` for clarity; curses modules stay untyped on `stdscr` unless you add types later.

---

## Environment

Every **curses** module sets:

```python
os.environ.setdefault("ESCDELAY", "0")
```

Immediately after imports (before other logic). Skipped only in `palette.py` and `settings_store.py` (no keyboard handling).

---

## Persistence

- **`settings.json`** is read and written **only** through `config/settings_store.py` (`load_settings`, `save_settings`).
- Do not duplicate `Path("settings.json")` or raw `json.dump` in screen modules.
- After mutations, call `save_settings(settings)` with the same dict you loaded and updated.

---

## Screen modules (`apps`, `states`, `colormode`)

### Public entrypoint

```text
def run_<name>(stdscr, color_mode: str) -> bool:
```

- **`stdscr`** — curses window from `curses.wrapper` / caller.
- **`color_mode`** — `"dark"` or `"light"` (session + saved preference as applicable).
- **Return value** — `True` if the user **persisted** a change that matters to the hub footer; `False` if they left without such a change (see each module’s logic).

First lines inside the function:

```python
curses.curs_set(0)
p = make_palette(color_mode)
```

### Nested helpers (inside `run_*`)

**`safe(y, x, text, attr=None)`** — clip to terminal, coerce `text` to `str`, default `attr` to `p["NORM"]`, use `attron`/`addstr`/`attroff`, **bare `except:`** only to swallow curses bounds errors. Never use `safe()` for horizontal rules (string slicing breaks box-drawing).

**`draw_header(title: str)`** — shared layout:

| Column / area | Content |
|---------------|---------|
| 0 | ` @ WENDY ` in `p["RED"]` |
| 9 | `title` — usually `p["DIM"]` for list hubs (`apps`, `states`); **`colormode`** uses `p["NORM"]` for the title and swaps control/title styling (see below) |
| Right | Controls string in `p["PINK"]` (`apps`, `states`) or `p["DIM"]` (`colormode`) |
| Row 1 | Full-width `p["RED"]` + `curses.ACS_HLINE` via `stdscr.hline` (not `safe`) |

Controls strings in use:

- `↑↓ navigate   enter select   esc back` — `apps`, `colormode`
- `↑↓ navigate   enter open   esc back` — `states`

### List layout

- First content row: **3**; spacing between rows: **2** (`row = 3 + i * 2`).
- Selected row: `>` at column **2**, label at column **4**, primary color `p["RED"]`.
- Scrollable lists: `list_rows = (h - 4) // 2`, adjust `scroll` so the cursor stays visible.

### Input

| Meaning | Representation |
|---------|----------------|
| Enter | `key in (curses.KEY_ENTER, 10, 13)` |
| Quit / back | `key in (ord("q"), 27)` |
| Up / down | `curses.KEY_UP` / `curses.KEY_DOWN` |

### Section comments

Major inner loops use a single-line banner:

```python
# ── App picker screen ─────────────────────────────────────────────
```

---

## `colorpicker.py` (exception)

- Does **not** call `make_palette` or touch `settings_store`; uses its own `init_pair` / pill colors for the splash.
- Exposes **`pick_color_mode(stdscr)`** returning `"light"` or `"dark"` (no `-> bool`; session-only).
- Inner `safe` takes **required** `attr` (no default).
- `cursor` **0 = light**, **1 = dark** (matches `OPTIONS` order).

---

## `palette.py`

- Single export: **`make_palette(color_mode: str)`** returning a `dict` with keys **`RED`**, **`PINK`**, **`NORM`**, **`DIM`**.
- No `os.environ` / `ESCDELAY`.
- Keep pair numbers and custom color indices stable unless you intentionally migrate all callers.

---

## `settings_store.py`

- **`REPO_ROOT`** derived from `Path(__file__).resolve().parent.parent`.
- **Constants** in `UPPER_SNAKE` (`SETTINGS_PATH`, `APP_KEYS`).
- **Private** helpers prefix `_` (`_empty_apps`).
- **`save_settings`** ends JSON with a **trailing newline** after `indent=2`.
- Prefer explicit `dict[str, …]` / `Any` where used; keep I/O and normalization in one place.

---

## Naming

- **`snake_case`** — functions, locals, JSON keys where you control them.
- **`UPPER_SNAKE`** — module-level constants (`CATEGORIES`, `MODES`, `APP_KEYS`).
- **Screen runners** — `run_apps`, `run_states`, `run_color_mode` (prefix `run_`).

---

## Formatting

- **Two blank lines** between top-level functions and classes (PEP 8).
- **One blank line** between logical groups inside long functions is fine.
- **No** heavy docstrings on every helper; a module docstring on `settings_store` is enough unless behavior is non-obvious.

---

## Design rules (short)

1. **One settings pipeline** — `settings_store` only.
2. **One palette for hub-style UIs** — `make_palette` for everything except `colorpicker`.
3. **Honest `bool` returns** — callers use them for footer messages; don’t save without setting `changed` / equivalent.
4. **Dividers** — always `hline` with `RED`, never `safe()` for full-width lines.

---

## Checklist for a new `config` screen

- [ ] `os.environ.setdefault("ESCDELAY", "0")` if curses
- [ ] `run_*(stdscr, color_mode: str) -> bool` (or documented exception like `pick_color_mode`)
- [ ] `curses.curs_set(0)` and `make_palette` where applicable
- [ ] `safe` + `draw_header` matching the table above
- [ ] Settings via `load_settings` / `save_settings` only
- [ ] Enter / Esc / arrows as in the table
- [ ] List rows from row 3, step 2
