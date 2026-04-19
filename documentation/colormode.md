# Wendy — Color Mode screen (`config/colormode.py`)

## Purpose

From the hub menu (**Color Mode**), lets the user choose **Dark** or **Light** and **writes `color_mode` to `settings.json`** via `config/settings_store.py`. This is the persisted preference; it is separate from the launch-only choice in `config/colorpicker.py`.

---

## Flow

```
main.py  →  run_color_mode(stdscr, color_mode)  →  load_settings()
                                                    save_settings() if changed
                                                    return bool
```

`main.py` passes the **current** session mode (from `pick_color_mode`). If the user selects a different mode and confirms, `settings["color_mode"]` is updated and saved. The hub then toggles its local `color_mode` and rebuilds the palette.

---

## Data

| Key | Values |
|-----|--------|
| `color_mode` | `"dark"` or `"light"` (stored lowercase) |

`MODES` in code is `["Dark", "Light"]` for display; the saved value uses `.lower()`.

---

## UI

- Header: `@ WENDY`, title `color mode` (title uses **`NORM`**), controls **`DIM`** (right-aligned): `↑↓ navigate   enter select   esc back`
- Rows 3 and 5 (with spacing): **Dark** and **Light** list items; selected uses `RED` and `>`; unselected `NORM`
- `enter` — apply if selection differs from incoming `color_mode`, then exit
- `q` / `esc` — exit without saving change (`changed` stays `False`)

---

## Return value

- `True` — user chose a mode **different** from the passed-in `color_mode` and confirmed (file written).
- `False` — user exited without changing, or chose the same mode as before.

---

## Palette

Uses `make_palette(color_mode)` from `config/palette.py` (`RED`, `PINK`, `NORM`, `DIM`).

---

## Design principles

- **Persistence** — this screen is how `color_mode` gets into `settings.json`.
- **Distinct from colorpicker** — launch picker = session UI; this screen = saved preference.
