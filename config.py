import curses
import random
import os
from colorpicker import pick_color_mode

os.environ.setdefault("ESCDELAY", "0")

MENU_ITEMS = [
    "Apps",
    "Color Mode",
    "States",
]

JOKES = [
    "I once sorted a list alphabetically. Still my greatest achievement.",
    "A terminal is just a GUI for people with taste.",
    "I'd tell you a UDP joke but you might not get it.",
    "It's not a bug, it's an undocumented feature. Donna would agree.",
    "There are 10 types of people. Those who get binary, and those who don't.",
    "Why do programmers prefer dark mode? Because light attracts bugs.",
    "I'm not lazy, I'm in power-saving mode.",
    "sudo make me a sandwich. Please.",
    "Tabs or spaces? I don't want to talk about it.",
    "The best code is the code you didn't have to write.",
    "I've seen things you people wouldn't believe. Mostly stack traces.",
    "Life is short. Use aliases.",
]

def reinit_pairs(color_mode: str) -> tuple:
    curses.start_color()
    curses.use_default_colors()
    if color_mode == "dark":
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_CYAN,    -1)
        curses.init_pair(3, curses.COLOR_WHITE,   -1)
        curses.init_pair(4, curses.COLOR_YELLOW,  -1)
        curses.init_pair(5, curses.COLOR_GREEN,   -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    else:
        curses.init_pair(1, curses.COLOR_RED,     -1)
        curses.init_pair(2, curses.COLOR_BLUE,    -1)
        curses.init_pair(3, curses.COLOR_BLACK,   -1)
        curses.init_pair(4, curses.COLOR_BLACK,   -1)
        curses.init_pair(5, curses.COLOR_GREEN,   -1)
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    RED   = curses.color_pair(1) | curses.A_BOLD
    CYAN  = curses.color_pair(2) | curses.A_BOLD
    NORM  = curses.color_pair(3)
    LABEL = curses.color_pair(4) | (curses.A_BOLD if color_mode == "light" else curses.A_NORMAL)
    GREEN = curses.color_pair(5) | curses.A_BOLD
    HINT  = curses.color_pair(6)
    return RED, CYAN, NORM, LABEL, GREEN, HINT

def run(stdscr):
    color_mode = pick_color_mode(stdscr)

    curses.curs_set(0)
    reinit_pairs(color_mode)
    RED, CYAN, NORM, LABEL, GREEN, HINT = reinit_pairs(color_mode)

    cursor = 0
    message = random.choice(JOKES)
    is_update = False

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

    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        # header
        controls = "↑↓ navigate   enter open   esc quit"
        safe(0, 0, " @ WENDY ", RED)
        safe(0, 9, "config", NORM)
        safe(0, w - len(controls) - 1, controls, HINT)

        try:
            stdscr.attron(RED)
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(RED)
        except:
            pass

        # menu
        for i, item in enumerate(MENU_ITEMS):
            row = 3 + i * 2
            if cursor == i:
                safe(row, 2, ">", RED)
                safe(row, 4, item, RED)
            else:
                safe(row, 4, item, NORM)

        # footer
        try:
            stdscr.attron(RED)
            stdscr.hline(h - 2, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(RED)
        except:
            pass
        msg_attr = NORM if is_update else HINT | curses.A_ITALIC
        msg_text = f" {message} " if is_update else f' "{message}" '
        safe(h - 1, 0, msg_text, msg_attr)

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
            message = random.choice(JOKES)
            is_update = False
        elif key == curses.KEY_DOWN:
            cursor = min(len(MENU_ITEMS) - 1, cursor + 1)
            message = random.choice(JOKES)
            is_update = False
        elif key in (curses.KEY_ENTER, 10, 13):
            selected = MENU_ITEMS[cursor]
            if selected == "States":
                from states import run_states
                changed = run_states(stdscr, color_mode)
                RED, CYAN, NORM, LABEL, GREEN, HINT = reinit_pairs(color_mode)
                if changed:
                    message = "States saved."
                    is_update = True
                else:
                    message = random.choice(JOKES)
                    is_update = False
            elif selected == "Apps":
                from apps import run_apps
                changed = run_apps(stdscr, color_mode)
                RED, CYAN, NORM, LABEL, GREEN, HINT = reinit_pairs(color_mode)
                if changed:
                    message = "App preferences updated."
                    is_update = True
                else:
                    message = random.choice(JOKES)
                    is_update = False
            elif selected == "Color Mode":
                from colormode import run_color_mode
                changed = run_color_mode(stdscr, color_mode)
                if changed:
                    color_mode = "light" if color_mode == "dark" else "dark"
                    RED, CYAN, NORM, LABEL, GREEN, HINT = reinit_pairs(color_mode)
                    message = f"Switched to {color_mode} mode. Good choice."
                else:
                    RED, CYAN, NORM, LABEL, GREEN, HINT = reinit_pairs(color_mode)
                    message = "Same as before. No judgment."
                is_update = True
        elif key == ord("q"):
            break

if __name__ == "__main__":
    curses.wrapper(run)
