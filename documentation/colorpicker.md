# Wendy — Launch color picker (`config/colorpicker.py`)

**Session UI conventions (`ESCDELAY`, why no `make_palette`):** `documentation/config-style.md` → **`colorpicker.py` (exception)**.

## Purpose

First screen when running `python3 main.py`. Chooses **light** or **dark** for **this run only** so `main.py` can call `make_palette()` before drawing the hub. Does **not** read or write `settings.json`.

## API

- **`pick_color_mode(stdscr)`** — blocks until confirm; returns **`"light"`** or **`"dark"`**.
- Called from **`main.py`** before the hub loop.

## vs persisted mode

Persisted light/dark is **`config/colormode.py`** (hub → **Color Mode**). See `documentation/colormode.md`.

## Content (unique to this screen)

- **Logo** — ASCII WENDY wordmark, centered, red.
- **Greeting** — one random Donna-style line, fixed for the whole screen (no re-roll on arrow keys).
- **Options** — LIGHT then DARK, pill styling; cursor **0 = light**, **1 = dark**; `↑`/`↓` and `enter` to confirm.
- Vertical placement: upper half (`top = max(1, h // 2 - 5)`), options below greeting.

Uses **its own** curses pairs (not `config/palette.py`) so the splash stays independent of hub colors.

## Principles

- Session-only — no file I/O.
- Minimal chrome — logo, greeting, two choices.
