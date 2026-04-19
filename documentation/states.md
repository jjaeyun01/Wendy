# Wendy — States screen (`config/states.py`)

## Purpose

Manage **named states** stored under `settings.json` → **`states`**. Each state is a string key mapping to an object (today always `{}` — reserved for future triggers/actions). Provides a scrollable list, add/delete shortcuts, and a placeholder detail view.

---

## Flow

```
main.py  →  run_states(stdscr, color_mode)  →  load_settings / save_settings via settings_store
```

Returns `True` if a state was added or deleted and saved; `False` if the user quits without such a change.

---

## Data shape

In the canonical file:

```json
{
  "states": {
    "Tony Stark": {}
  }
}
```

New states are added as `settings["states"][name] = {}`.

---

## Screens

### List screen

- Header: `states`, controls `↑↓ navigate   enter open   esc back` (`PINK`)
- Scrollable list of state names (same row spacing pattern as other lists)
- Empty list: message `No states yet.`
- Footer when not adding: `n  new   d  delete` (`DIM`, bottom-right)

### Add mode (`n`)

- Footer becomes a prompt: `new state: ` with inline input and cursor block
- `enter` — commit non-empty name, save, resort list
- `esc` — cancel

### Detail screen (`enter` on a state)

- Header: `states  /  {name}`
- Body: `Triggers and actions coming soon.`
- `q` / `esc` — back to list

### Delete (`d`)

- Removes the highlighted state from `settings["states"]` and saves.

---

## Navigation

| Key | Action |
|-----|--------|
| `↑` / `↓` | Move cursor (list) |
| `enter` | Open detail placeholder |
| `n` | New state (prompt) |
| `d` | Delete selected state |
| `q` / `esc` | Back / quit |

---

## Palette

Uses `make_palette(color_mode)` from `config/palette.py`.

---

## Design principles

- **Honest return** — `True` only when the file was actually updated (add/delete).
- **Placeholder detail** — room for future triggers/actions without changing the `states` map shape yet.
