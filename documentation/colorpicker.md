# Wendy — Launch color picker (`config/colorpicker.py`)

## Purpose

The first screen when running `python3 main.py`. It captures **light or dark** for the **current session** so the hub and submenus can call `make_palette()` with a consistent mode before drawing the main menu.

---

## API

- **`pick_color_mode(stdscr)`** — blocking UI loop; returns `"light"` or `"dark"`.
- Invoked from `main.py` as `color_mode = pick_color_mode(stdscr)` **before** the hub loop.

---

## Relationship to `settings.json`

The launch picker does **not** read or write `settings.json`. It only affects the initial `color_mode` passed into `main.run()`.

Persisted light/dark for future sessions is handled separately by **`config/colormode.py`** when the user opens **Color Mode** from the hub.

---

## Visual style

### Logo

ASCII **WENDY** wordmark in bold red, centered.

### Greeting

One line chosen at random from three Donna-style lines, **fixed for the duration of that screen** (no re-roll on arrow keys).

### Selection

Vertical list: **LIGHT** then **DARK** (cursor 0 = light, 1 = dark). `↑` / `↓` to move, `enter` to confirm. Selected row: `>` in red + pill styling; unselected row dimmed.

Content is placed in the upper half of the terminal (`top = max(1, h // 2 - 5)`, options below the greeting).

---

## Implementation notes

- Uses its **own** curses color pairs (red, white, cyan, light/dark pills) — not `config/palette.py`. That keeps the splash independent of the hub palette.
- `ESCDELAY` is set to `0` for responsive key handling (same as other Wendy modules).

---

## Design principles

- **Session-only** — no file I/O; separates “how I look this run” from “what I saved for later.”
- **Minimal** — no extra prompts beyond logo, greeting, and two options.
