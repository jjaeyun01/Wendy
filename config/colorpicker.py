import curses
import os
import random

os.environ.setdefault("ESCDELAY", "0")

def pick_color_mode(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_RED,   -1)
    curses.init_pair(2, curses.COLOR_WHITE, -1)
    curses.init_pair(3, curses.COLOR_CYAN,  -1)
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)

    RED        = curses.color_pair(1) | curses.A_BOLD
    WHITE      = curses.color_pair(2)
    CYAN       = curses.color_pair(3) | curses.A_BOLD
    LIGHT_PILL = curses.color_pair(4) | curses.A_BOLD
    DARK_PILL  = curses.color_pair(5) | curses.A_BOLD

    cursor = 0  # 0 = light, 1 = dark

    # locked on launch — never changes while navigating
    greeting = random.choice([
        "\"Before we get started, let's make sure you can actually see me.\"",
        "\"You're going to be staring at me all day. Choose wisely.\"",
        "\"Aesthetics matter. Donna taught me that.\"",
    ])

    LOGO = [
        " _    _ _____ _   _________   __",
        "| |  | |  ___| \\ | |  _  \\ \\ / /",
        "| |  | | |__ |  \\| | | | |\\ V / ",
        "| |/\\| |  __|| . ` | | | | \\ /  ",
        "\\  /\\  / |___| |\\  | |/ /  | |  ",
        " \\/  \\/\\____/\\_| \\_/___/   \\_/  ",
    ]

    OPTIONS = [
        ("  LIGHT  ", LIGHT_PILL),
        ("  DARK   ", DARK_PILL),
    ]

    def safe(y, x, text, attr):
        h, w = stdscr.getmaxyx()
        if y < 0 or y >= h or x < 0 or x >= w:
            return
        try:
            stdscr.attron(attr)
            stdscr.addstr(y, x, str(text)[:w - x - 1])
            stdscr.attroff(attr)
        except:
            pass

    while True:
        h, w = stdscr.getmaxyx()
        stdscr.erase()

        top = max(1, h // 2 - 5)

        # logo
        for i, line in enumerate(LOGO):
            safe(top + i, max(0, (w - len(line)) // 2), line, RED)

        # greeting — locked, never re-randomized
        safe(top + 7, max(0, (w - len(greeting)) // 2), greeting, WHITE | curses.A_ITALIC)



        # vertical option list
        pill_w = max(len(lbl) for lbl, _ in OPTIONS)
        ox = max(0, (w - pill_w) // 2)
        oy = top + 10

        for i, (label, pill_attr) in enumerate(OPTIONS):
            row = oy + i * 2
            is_sel = (cursor == i)
            if is_sel:
                safe(row, ox - 2, ">", RED)
                safe(row, ox,     label, pill_attr)
            else:
                safe(row, ox - 2, " ", WHITE)
                safe(row, ox,     label, pill_attr | curses.A_DIM)


        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP:
            cursor = max(0, cursor - 1)
        elif key == curses.KEY_DOWN:
            cursor = min(len(OPTIONS) - 1, cursor + 1)
        elif key in (curses.KEY_ENTER, 10, 13):
            return "light" if cursor == 0 else "dark"

if __name__ == "__main__":
    result = curses.wrapper(pick_color_mode)
    print(f"\nColor mode selected: {result}")
