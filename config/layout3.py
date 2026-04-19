"""
Three-pane workspace layouts (Contents has three apps selected).
UI matches patterns in config/states.py: passed-in palette, safe, draw_header.
"""

import curses
import os

os.environ.setdefault("ESCDELAY", "0")

# ── Three equal regions A, B, C — ids unique within n=3 ───────────────────────

TAG_ABC = ["A: content", "B: content", "C: content"]

LAYOUTS_3 = [
    {
        "id": 1,
        "name": "Equal Thirds",
        "tag_lines": TAG_ABC,
        "art": [
            "+--------+-------+--------+",
            "|        |       |        |",
            "|   A    |   B   |   C    |",
            "|        |       |        |",
            "|        |       |        |",
            "|        |       |        |",
            "+--------+-------+--------+",
        ],
    },
    {
        "id": 2,
        "name": "Side + Stacked",
        "tag_lines": TAG_ABC,
        "art": [
            "+------------+------------+",
            "|            |     B      |",
            "|     A      |            |",
            "|            +------------+",
            "|            |     C      |",
            "|            |            |",
            "+------------+------------+",
        ],
    },
    {
        "id": 3,
        "name": "Stacked + Side",
        "tag_lines": TAG_ABC,
        "art": [
            "+------------+------------+",
            "|     B      |            |",
            "|            |     A      |",
            "+------------+            |",
            "|     C      |            |",
            "|            |            |",
            "+------------+------------+",
        ],
    },
]


def pick_layout_3(stdscr, p, safe, draw_header, header_title: str) -> int | None:
    """
    List three layout options with ASCII preview. Return layout id (1–3), or None on esc.
    """
    layouts = LAYOUTS_3
    selected = 0

    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")

        for i, layout in enumerate(layouts):
            row = 3 + i * 2
            is_sel = i == selected
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, f"{layout['id']:02d}  {layout['name']}", attr)

        layout = layouts[selected]
        art = layout["art"]
        art_w = len(art[0]) if art else 0
        art_col = max(4, w - art_w - 4)
        art_row = 3

        for j, line in enumerate(art):
            safe(art_row + j, art_col, line, p["RED"])

        y_after = art_row + len(art) + 1
        if layout.get("tag_lines"):
            for k, line in enumerate(layout["tag_lines"]):
                safe(y_after + k, art_col, line, p["DIM"])
        elif layout.get("tag"):
            safe(y_after, art_col, layout["tag"], p["DIM"])

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        if key == curses.KEY_UP:
            selected = max(0, selected - 1)
        elif key == curses.KEY_DOWN:
            selected = min(len(layouts) - 1, selected + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return layouts[selected]["id"]


def _cat_label(key: str) -> str:
    return {
        "browser": "Browser",
        "ide": "IDE",
        "music": "Music",
        "notes": "Notes",
        "terminal": "Terminal",
    }.get(key, key.replace("_", " ").title())


def _pick_slot(
    stdscr,
    p,
    safe,
    draw_header,
    header_title: str,
    slot_letter: str,
    options: list[str],
) -> str | None:
    """Pick one category key from options. None on esc. Single option returns it."""
    if len(options) == 1:
        return options[0]
    cursor = 0
    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")
        safe(3, 4, f"Region {slot_letter} — which content?", p["DIM"])
        for i, opt in enumerate(options):
            row = 5 + i * 2
            label = _cat_label(opt)
            is_sel = i == cursor
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, label, attr)
        stdscr.refresh()
        key = stdscr.getch()
        if key in (ord("q"), 27):
            return None
        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(options) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return options[cursor]


def assign_slots_abc(
    stdscr,
    p,
    safe,
    draw_header,
    header_base: str,
    apps: list[str],
) -> dict[str, str] | None:
    """
    Map regions A, B, C to the three enabled content categories (lowercase keys).
    Returns {"A": k1, "B": k2, "C": k3} or None if cancelled.
    """
    if len(apps) != 3:
        return None
    remaining = sorted(apps)
    out: dict[str, str] = {}
    for letter in ("A", "B"):
        title = f"{header_base}  /  {letter}"
        picked = _pick_slot(stdscr, p, safe, draw_header, title, letter, remaining)
        if picked is None:
            return None
        out[letter] = picked
        remaining.remove(picked)
    c_key = remaining[0]
    while True:
        stdscr.erase()
        draw_header(f"{header_base}  /  C", "enter confirm   esc back")
        safe(3, 4, f"Region C → {_cat_label(c_key)}", p["NORM"])
        safe(5, 4, "Last remaining content.", p["DIM"])
        stdscr.refresh()
        key = stdscr.getch()
        if key in (ord("q"), 27):
            return None
        if key in (curses.KEY_ENTER, 10, 13):
            break
    out["C"] = c_key
    return out
