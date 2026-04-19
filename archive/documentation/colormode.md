# Wendy — Color Mode (`config/colormode.py`)

**Shared screen patterns (`run_*`, palette, `safe`, keys):** `documentation/config-style.md` → **Screen modules** (this module uses **`NORM`/`DIM`** for title/controls instead of the usual **`DIM`/`PINK`** — noted there).

## Purpose

From the hub (**Color Mode**), choose **Dark** or **Light** and **save** `color_mode` to `settings.json` via `config/settings_store.py`. This is the persisted preference; the launch picker (`config/colorpicker.py`) is session-only.

## Flow

`main.py` calls `run_color_mode(stdscr, color_mode)` with the current session mode. On confirm with a **different** mode, `settings["color_mode"]` is updated and saved; the hub then flips local `color_mode` and rebuilds the palette.

## Data

| Key | Stored value |
|-----|----------------|
| `color_mode` | `"dark"` or `"light"` (lowercase) |

`MODES` in code: `["Dark", "Light"]` for labels; saved value uses `.lower()`.

## Behavior

- **`enter`** — if chosen mode ≠ incoming `color_mode`, save and set **`changed`**; then exit.
- **`q` / `esc`** — exit without persisting a change (`changed` **False**).

List of **Dark** / **Light** follows the shared list layout (row 3, step 2) in `config-style.md`.

## Return value

- **`True`** — user confirmed a mode **different** from the one passed in (file written).
- **`False`** — same mode as before, or quit without applying.

## Principles

- This screen is how **`color_mode`** enters `settings.json`.
- Distinct from **`colorpicker`** — launch vs saved preference.
