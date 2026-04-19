# Wendy — States (`config/states.py`)

**Shared patterns (`safe`, `draw_header`, lists, scroll, default keys):** `documentation/config-style.md`. This module **passes custom `controls`** strings into `draw_header` on workspace / app screens.

## Purpose

**States** are named presets under `settings.json` → **`states`**. Each state has a **workspace map** (IDs `1`–`9`, then `A`–`Z`). Each workspace can enable up to **four** of the five global categories (browser, IDE, music, notes, terminal) and optional **URLs** for browser / browser-like music.

Persistence: **`load_settings` / `save_settings`** only.

## Entry

`run_states(stdscr, color_mode) -> bool` — **`True`** if the user saved (new/delete state, or nested workspace changes). **`False`** if they quit the **state list** with `q`/`esc` without such saves.

## Data shape

```json
{
  "states": {
    "Work": {
      "workspaces": {
        "1": {
          "apps": ["browser", "ide", "music", "notes"],
          "browser_url": "https://example.com",
          "music_url": "https://music.example.com",
          "layout": {
            "n": 3,
            "id": 2,
            "slots": { "A": "browser", "B": "ide", "C": "music" }
          }
        }
      }
    }
  }
}
```

| Field | Meaning |
|--------|---------|
| `workspaces` | Map of workspace ID → config. |
| `apps` | Lowercase category names; **max four** per workspace. |
| `browser_url` | Set when Browser is enabled; cleared when toggled off. |
| `music_url` | When Music is enabled **and** global `apps.music` matches browser-like names (`BROWSER_HINTS` / same idea as `apps.py`). |
| `layout` | Optional. **`n`** = pane count when chosen (1–4); **`id`** = layout variant. If **`n` = 3**, **`slots`** maps **`A`**, **`B`**, **`C`** to category keys from **Contents** (each of the three apps appears exactly once). |

New states start as **`{"workspaces": {}}`**.

## Screen 1 — State list

- Header title **`states`**; controls `↑↓ navigate   enter open   esc back`.
- Sorted names; scrollable list; empty → `No states yet.`
- Footer **`n  new   d  delete`** when not adding.
- **`n`** — prompt `new state: `; **`enter`** commits non-empty name.
- **`d`** — delete highlighted state.
- **`enter`** — open workspace grid for that state.
- **`q` / `esc`** — leave `run_states`.

## Screen 2 — Workspace grid (`_run_workspaces`)

- **`WORKSPACE_IDS`**: `"1"`…`"9"`, `"A"`…`"Z"`; **9 columns** (`COLS = 9`).
- Cursor: **`>`** left of ID. **RED** = cursor; **PINK** = has apps; **NORM** = empty.
- Footer: `{id}: {categories…}` or `empty`.
- **`↑`/`↓`** move by grid row (step 9 indices); **`←`/`→`** by one cell.
- **`enter`** — open the **workspace menu** (below), not the app screen directly.
- **`esc` / `q`** — back to state list.

## Screen 3 — Workspace menu (`_run_workspace_menu`)

After **`enter`** on a workspace:

- Header: `states  /  {state}  /  {ws_id}`; controls `↑↓ navigate   enter open   esc back`.
- Two rows in **alphabetical** order: **Contents**, then **Layouts**. Default highlight: **Contents** (first row).
- **`enter`** on **Contents** → **Screen 4** (`_run_ws_apps`). **`esc` / `q`** there saves workspace data and returns **to this menu** (not to the grid).
- **`enter`** on **Layouts** → **Screen 5** (`_run_workspace_layouts`). **`esc` / `q`** from the layout list returns to this menu.
- **`esc` / `q`** on **this menu** — back to the workspace grid. Return value is **`True`** if **Contents** or **Layouts** saved at least once while this menu was open.

## Screen 4 — Workspace contents (`_run_ws_apps`)

- Toggle categories with **`enter`** (max four on). Removing browser/music clears URLs.
- Adding **Browser** prompts for **`browser_url`**; adding **Music** prompts for **`music_url`** only if `music_is_browser(settings)`.
- **`esc`/`q`** (outside URL input) — write `apps`, `browser_url`, `music_url` for this `ws_id` and exit (returns **`True`**).

## Screen 5 — Layouts (`_run_workspace_layouts`)

- **`n`** = `len(apps)` for this workspace. **0 apps** → message to configure **Contents** first; **`esc`** back to the workspace menu.
- **`n` = 3** → **`layout3.pick_layout_3`** (layouts 1–3), then **`layout3.assign_slots_abc`**: choose which **Contents** category goes to **A**, then **B**, then confirm **C** (last remaining).
- **`n` = 1, 2, or 4** → **`_pick_layout_list`** with **`LAYOUTS_1`**, **`LAYOUTS_2`**, or **`LAYOUTS_4`** (no `slots`).
- Saves **`layout`** including **`slots`** when **`n` = 3**; **`esc`** on any step cancels without saving.

## Implementation notes

- **`music_is_browser(settings)`** — reads global **`settings["apps"]["music"]`** against browser hints.
- **`enabled`** — `set` of lowercase category names; stored sorted.

## Principles

- State → workspace → category + URL layering.
- **Four** categories max per workspace.
