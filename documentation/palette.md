# Wendy — Terminal palette (`config/palette.py`)

## Purpose

Builds a small dictionary of **curses** attributes for the hub and submenus (`RED`, `PINK`, `NORM`, `DIM`) from a string **`color_mode`**: `"dark"` or `"light"`.

---

## API

```text
make_palette(color_mode: str) -> dict
```

Returns keys:

| Key | Typical use |
|-----|-------------|
| `RED` | Brand accents, wordmark, dividers, selection (`A_BOLD` + pair 1) |
| `PINK` | Controls hints, accents (`A_BOLD` + pair 2) |
| `NORM` | Default foreground (pair 3 — white on dark, black on light) |
| `DIM` | `NORM` + `A_DIM` |

---

## Colors

When `curses.can_change_color()` is true, custom colors **16** and **17** approximate `#832e31` (red) and `#df9396` (pink). Otherwise pair 1 uses `COLOR_RED` and pair 2 uses `COLOR_MAGENTA`.

---

## Consumers

`main.py`, `config/apps.py`, `config/states.py`, `config/colormode.py` — **not** `config/colorpicker.py`, which uses its own pairs for the launch screen.

---

## Design principles

- **Central palette** — consistent look across post-picker UI.
- **Two modes** — dark vs light only affects `NORM` (pair 3 foreground); red/pink pairs stay defined the same way.
