import curses
import random
import os
from config.colorpicker import pick_color_mode
from config.palette import make_palette

os.environ.setdefault("ESCDELAY", "0")

MENU_ITEMS = [
    "Apps",
    "Color Mode",
    "States",
    "Motion",
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

def run(stdscr):
    color_mode = pick_color_mode(stdscr)

    curses.curs_set(0)
    p = make_palette(color_mode)

    cursor = 0
    message = random.choice(JOKES)
    is_update = False

    def safe(y, x, text, attr=None):
        if attr is None:
            attr = p["NORM"]
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
        safe(0, 0, " @ WENDY ", p["RED"])
        safe(0, 9, "config", p["DIM"])
        safe(0, w - len(controls) - 1, controls, p["PINK"])

        try:
            stdscr.attron(p["RED"])
            stdscr.hline(1, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(p["RED"])
        except:
            pass

        # menu
        for i, item in enumerate(MENU_ITEMS):
            row = 3 + i * 2
            if cursor == i:
                safe(row, 2, ">", p["RED"])
                safe(row, 4, item, p["RED"])
            else:
                safe(row, 4, item, p["NORM"])

        # footer
        try:
            stdscr.attron(p["RED"])
            stdscr.hline(h - 2, 0, curses.ACS_HLINE, w - 1)
            stdscr.attroff(p["RED"])
        except:
            pass
        msg_attr = p["NORM"] if is_update else p["PINK"]
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
                from config.states import run_states
                changed = run_states(stdscr, color_mode)
                p = make_palette(color_mode)
                if changed:
                    message = "States saved."
                    is_update = True
                else:
                    message = random.choice(JOKES)
                    is_update = False
            elif selected == "Apps":
                from config.apps import run_apps
                changed = run_apps(stdscr, color_mode)
                p = make_palette(color_mode)
                if changed:
                    message = "App preferences updated."
                    is_update = True
                else:
                    message = random.choice(JOKES)
                    is_update = False
            elif selected == "Color Mode":
                from config.colormode import run_color_mode
                changed = run_color_mode(stdscr, color_mode)
                if changed:
                    color_mode = "light" if color_mode == "dark" else "dark"
                    message = f"Switched to {color_mode} mode. Good choice."
                else:
                    message = "Same as before. No judgment."
                p = make_palette(color_mode)
                is_update = True
            elif selected == "Motion":
                from config.motion import run_motion
                changed = run_motion(stdscr, color_mode)
                p = make_palette(color_mode)
                if changed:
                    message = "Motion configuration updated."
                    is_update = True
                else:
                    message = random.choice(JOKES)
                    is_update = False
        elif key == ord("q"):
            break

if __name__ == "__main__":
    curses.wrapper(run)
