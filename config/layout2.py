"""
Two-pane workspace layouts (Contents has two apps selected).
UI matches config/layout3.py: palette, safe, draw_header.
"""

import curses
import os

from config.layout_common import cat_label
from config.layout3 import _pick_slot

os.environ.setdefault("ESCDELAY", "0")

TAG_PLACEHOLDER = ["A: —", "B: —"]

LAYOUTS_2 = [
    {
        "id": 1,
        "name": "Side by side",
        "art": [
            "+-------------+-------------+",
            "|             |             |",
            "|      A      |      B      |",
            "|             |             |",
            "+-------------+-------------+",
        ],
    },
    {
        "id": 2,
        "name": "Stacked",
        "art": [
            "+----------------------------+",
            "|            A               |",
            "+----------------------------+",
            "|            B               |",
            "+----------------------------+",
        ],
    },
]


def _ab_tag_lines(
    slots: dict[str, str] | None,
    apps: list[str] | None,
) -> list[str]:
    """
    Right-hand legend: prefer saved A/B mapping; if missing or stale, show the two
    Contents apps in sorted order (same idea as layout1’s auto A: line).
    """
    if apps is not None and len(apps) == 2:
        if (
            slots
            and all(k in slots for k in ("A", "B"))
            and set(slots.values()) == set(apps)
        ):
            return [
                f"A: {cat_label(slots['A'])}",
                f"B: {cat_label(slots['B'])}",
            ]
        a0, a1 = sorted(apps)
        return [f"A: {cat_label(a0)}", f"B: {cat_label(a1)}"]
    if not slots or not all(k in slots for k in ("A", "B")):
        return list(TAG_PLACEHOLDER)
    return [
        f"A: {cat_label(slots['A'])}",
        f"B: {cat_label(slots['B'])}",
    ]


def pick_layout_2(
    stdscr,
    p,
    safe,
    draw_header,
    header_title: str,
    *,
    current_layout_id: int | None = None,
    cursor_start_id: int | None = None,
    slots: dict[str, str] | None = None,
    apps: list[str] | None = None,
) -> int | None:
    layouts = LAYOUTS_2
    selected = 0
    start_id = cursor_start_id if cursor_start_id is not None else current_layout_id
    if start_id is not None:
        for i, lo in enumerate(layouts):
            if lo["id"] == start_id:
                selected = i
                break

    while True:
        _, w = stdscr.getmaxyx()
        stdscr.erase()
        draw_header(header_title, "↑↓ navigate   enter select   esc back")

        for i, layout in enumerate(layouts):
            row = 3 + i * 2
            is_cursor = i == selected
            is_saved = current_layout_id is not None and layout["id"] == current_layout_id
            cur = ">" if is_cursor else " "
            if is_cursor:
                attr = p["RED"]
            elif is_saved:
                attr = p["RED"]
            else:
                attr = p["NORM"]
            safe(row, 2, cur, attr)
            safe(row, 4, f"{layout['id']:02d}  {layout['name']}", attr)

        layout = layouts[selected]
        art = layout["art"]
        art_w = len(art[0]) if art else 0
        art_col = max(4, w - art_w - 4)
        art_row = 3

        for j, line in enumerate(art):
            safe(art_row + j, art_col, line, p["RED"])

        tag_lines = _ab_tag_lines(slots, apps)
        if tag_lines:
            max_tag_len = max(len(t) for t in tag_lines)
            gap = 2
            tag_start_col = art_col + art_w + gap
            if tag_start_col + max_tag_len < w:
                for k, line in enumerate(tag_lines):
                    safe(art_row + k, tag_start_col, line, p["DIM"])
            else:
                y0 = art_row + len(art)
                for k, line in enumerate(tag_lines):
                    safe(y0 + k, art_col, line, p["DIM"])

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


def assign_slots_ab(
    stdscr,
    p,
    safe,
    draw_header,
    header_base: str,
    apps: list[str],
) -> dict[str, str] | None:
    """
    Map regions A and B to the two enabled content categories.
    Pick A, then B is the remaining app. Returns {"A": k1, "B": k2} or None on esc.
    """
    if len(apps) != 2:
        return None

    letters = ["A", "B"]
    assigned: dict[str, str] = {}
    cursor = 0

    while True:
        if "A" in assigned and "B" not in assigned:
            remaining = [a for a in sorted(apps) if a not in assigned.values()]
            assigned["B"] = remaining[0]

        all_done = all(x in assigned for x in letters)

        stdscr.erase()
        hint = (
            "enter select   esc layout"
            if not all_done
            else "enter confirm   esc layout"
        )
        draw_header(header_base, hint)

        for i, letter in enumerate(letters):
            row = 3 + i * 2
            is_sel = i == cursor
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            value = cat_label(assigned[letter]) if letter in assigned else "—"
            val_attr = p["DIM"] if letter == "B" and "B" not in assigned else p["NORM"]
            if is_sel:
                val_attr = attr
            safe(row, 2, cur, attr)
            safe(row, 4, f"Region {letter}", attr)
            safe(row, 16, value, val_attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key in (ord("q"), 27):
            return None
        elif key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(letters) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if all_done:
                return assigned
            letter = letters[cursor]
            if letter == "B":
                continue
            available = [a for a in sorted(apps) if a not in assigned.values()
                         or assigned.get(letter) == a]
            if letter in assigned:
                available = [assigned[letter]] + [
                    a for a in sorted(apps)
                    if a != assigned[letter] and a not in assigned.values()
                ]
            picked = _pick_slot(
                stdscr,
                p,
                safe,
                draw_header,
                f"{header_base}  /  {letter}",
                letter,
                available,
            )
            if picked is not None:
                if letter in assigned:
                    assigned.pop(letter)
                    if letter == "A" and "B" in assigned:
                        assigned.pop("B")
                assigned[letter] = picked
                for j, s in enumerate(letters):
                    if s not in assigned:
                        cursor = j
                        break
