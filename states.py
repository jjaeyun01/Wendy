import curses
import json
import os
from pathlib import Path

os.environ.setdefault("ESCDELAY", "0")

SETTINGS_PATH = Path("settings.json")


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text())
        except Exception:
            pass
    return {}


def save_settings(settings: dict) -> None:
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2))


def run_states(stdscr, color_mode: str) -> bool:
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    if color_mode == "dark":
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_WHITE,   -1)
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)
    else:
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_BLACK,   -1)
        curses.init_pair(3, curses.COLOR_MAGENTA, -1)

    RED  = curses.color_pair(1) | curses.A_BOLD
    NORM = curses.color_pair(2)
    DIM  = curses.color_pair(2) | curses.A_DIM
    HINT = curses.color_pair(3)

    def safe(y, x, text, attr=None):
        if attr is None:
            attr = NORM
        h, w = stdscr.getmaxyx()
        text = str(text)
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        try:
            stdscr.attron(attr)
            stdscr.addstr(y, x, text[:w - x - 1])
            stdscr.attroff(attr)
        except:
            pass

    def draw_header(title: str) -> None:
        h, w = stdscr.getmaxyx()
        controls = "↑↓ navigate   enter open   esc back"
        safe(0, 0, " @ WENDY ", RED)
        safe(0, 9, title, NORM)
        safe(0, w - len(controls) - 1, controls, HINT)
        try:
            stdscr.attron(RED)
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(RED)
        except:
            pass

    def draw_shortcuts() -> None:
        h, w = stdscr.getmaxyx()
        shortcuts = "n  new   d  delete"
        safe(h - 1, w - len(shortcuts) - 1, shortcuts, DIM)

    settings = load_settings()
    states = sorted(settings.get("states", {}).keys())
    cursor = 0
    scroll = 0
    changed = False
    adding = False
    input_buf = ""

    # ── States list screen ────────────────────────────────────────────────────
    while True:
        h, w = stdscr.getmaxyx()
        list_rows = (h - 4) // 2
        stdscr.erase()
        draw_header("states")

        if not states:
            safe(3, 4, "No states yet.", DIM)
        else:
            if cursor < scroll:
                scroll = cursor
            elif cursor >= scroll + list_rows:
                scroll = cursor - list_rows + 1

            for screen_i, idx in enumerate(range(scroll, min(scroll + list_rows, len(states)))):
                row = 3 + screen_i * 2
                name = states[idx]
                if cursor == idx:
                    safe(row, 2, ">", RED)
                    safe(row, 4, name, RED)
                else:
                    safe(row, 4, name, NORM)

        # inline new-state input
        if adding:
            prompt = "new state: "
            safe(h - 1, 0, prompt + input_buf + "█", HINT)
        else:
            draw_shortcuts()

        stdscr.refresh()

        if adding:
            curses.curs_set(0)
            key = stdscr.getch()
            if key in (curses.KEY_ENTER, 10, 13):
                name = input_buf.strip()
                if name:
                    if "states" not in settings:
                        settings["states"] = {}
                    settings["states"][name] = {}
                    save_settings(settings)
                    states = sorted(settings["states"].keys())
                    cursor = states.index(name)
                    changed = True
                adding = False
                input_buf = ""
            elif key == 27:
                adding = False
                input_buf = ""
            elif key in (curses.KEY_BACKSPACE, 127):
                input_buf = input_buf[:-1]
            elif 32 <= key <= 126:
                input_buf += chr(key)
        else:
            key = stdscr.getch()

            if key == curses.KEY_UP:
                cursor = max(0, cursor - 1)
            elif key == curses.KEY_DOWN:
                cursor = min(max(0, len(states) - 1), cursor + 1)
            elif key in (curses.KEY_ENTER, 10, 13):
                if states:
                    chosen = states[cursor]

                    # ── State detail screen (placeholder) ─────────────────────
                    while True:
                        h, w = stdscr.getmaxyx()
                        stdscr.erase()
                        draw_header(f"states  /  {chosen}")
                        safe(3, 4, "Triggers and actions coming soon.", DIM)
                        stdscr.refresh()
                        key = stdscr.getch()
                        if key in (ord("q"), 27):
                            break

            elif key == ord("n"):
                adding = True
                input_buf = ""
            elif key == ord("d"):
                if states:
                    name = states[cursor]
                    settings.get("states", {}).pop(name, None)
                    save_settings(settings)
                    states = sorted(settings.get("states", {}).keys())
                    cursor = min(cursor, max(0, len(states) - 1))
                    changed = True
            elif key in (ord("q"), 27):
                break

    return changed
