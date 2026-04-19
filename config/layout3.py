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

        tag_lines = layout.get("tag_lines") or []
        if tag_lines:
            max_tag_len = max(len(t) for t in tag_lines)
            gap = 2
            tag_start_col = art_col + art_w + gap
            # Same vertical level as the layout list / art top — beside the diagram when it fits
            if tag_start_col + max_tag_len < w:
                for k, line in enumerate(tag_lines):
                    safe(art_row + k, tag_start_col, line, p["DIM"])
            else:
                # Narrow terminal: tuck tags directly under the art (no extra blank row)
                y0 = art_row + len(art)
                for k, line in enumerate(tag_lines):
                    safe(y0 + k, art_col, line, p["DIM"])
        elif layout.get("tag"):
            safe(art_row + len(art), art_col, layout["tag"], p["DIM"])

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
        for i, opt in enumerate(options):
            row = 3 + i * 2
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

    Flow: single A/B/C screen. cursor moves between slots. enter on a slot opens
    content picker, returns to ABC screen with slot filled. C is auto-assigned once
    A and B are filled. Final enter (on any slot when all filled) confirms.
    """
    if len(apps) != 3:
        return None

    slots = ["A", "B", "C"]
    assigned: dict[str, str] = {}
    cursor = 0  # which slot row is highlighted

    while True:
        # auto-assign C when A and B are done
        if "A" in assigned and "B" in assigned and "C" not in assigned:
            remaining = [a for a in sorted(apps) if a not in assigned.values()]
            assigned["C"] = remaining[0]

        all_done = all(s in assigned for s in slots)

        stdscr.erase()
        hint = "enter select   esc back" if not all_done else "enter confirm   esc back"
        draw_header(header_base, hint)

        for i, letter in enumerate(slots):
            row = 3 + i * 2
            is_sel = i == cursor
            cur = ">" if is_sel else " "
            attr = p["RED"] if is_sel else p["NORM"]
            value = _cat_label(assigned[letter]) if letter in assigned else "—"
            # dim C slot until auto-assigned
            val_attr = p["DIM"] if letter == "C" and "C" not in assigned else p["NORM"]
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
            cursor = min(len(slots) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            if all_done:
                return assigned
            letter = slots[cursor]
            if letter == "C":
                # C is auto-assigned, skip
                continue
            available = [a for a in sorted(apps) if a not in assigned.values()
                         or assigned.get(letter) == a]
            # include current assignment so user can re-pick
            if letter in assigned:
                available = [assigned[letter]] + [
                    a for a in sorted(apps)
                    if a != assigned[letter] and a not in assigned.values()
                ]
            picked = _pick_slot(
                stdscr, p, safe, draw_header,
                f"{header_base}  /  {letter}", letter, available
            )
            if picked is not None:
                # if re-picking, free old value
                if letter in assigned:
                    old = assigned.pop(letter)
                    # also clear C if it was auto-assigned from old value
                    if assigned.get("C") != old and "C" in assigned:
                        pass
                    elif "C" in assigned:
                        assigned.pop("C")
                assigned[letter] = picked
                # advance cursor to next unfilled slot
                for j, s in enumerate(slots):
                    if s not in assigned:
                        cursor = j
                        break
