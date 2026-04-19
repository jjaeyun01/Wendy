import curses


def make_palette(color_mode: str) -> dict:
    curses.start_color()
    curses.use_default_colors()

    if color_mode == "dark":
        curses.init_pair(1, curses.COLOR_RED,     -1)  # RED
        curses.init_pair(2, curses.COLOR_WHITE,   -1)  # DIM
        curses.init_pair(3, curses.COLOR_WHITE,   -1)  # NORM
        curses.init_pair(4, curses.COLOR_YELLOW,  -1)  # LABEL
        curses.init_pair(5, curses.COLOR_GREEN,   -1)  # GREEN
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # HINT
        curses.init_pair(7, curses.COLOR_CYAN,    -1)  # CYAN

        return {
            "RED":   curses.color_pair(1) | curses.A_BOLD,
            "DIM":   curses.color_pair(2) | curses.A_DIM,
            "NORM":  curses.color_pair(3),
            "LABEL": curses.color_pair(4),
            "GREEN": curses.color_pair(5) | curses.A_BOLD,
            "HINT":  curses.color_pair(6),
            "CYAN":  curses.color_pair(7) | curses.A_BOLD,
        }

    else:
        curses.init_pair(1, curses.COLOR_RED,     -1)  # RED
        curses.init_pair(2, curses.COLOR_BLACK,   -1)  # DIM
        curses.init_pair(3, curses.COLOR_BLACK,   -1)  # NORM
        curses.init_pair(4, curses.COLOR_BLACK,   -1)  # LABEL
        curses.init_pair(5, curses.COLOR_GREEN,   -1)  # GREEN
        curses.init_pair(6, curses.COLOR_MAGENTA, -1)  # HINT
        curses.init_pair(7, curses.COLOR_BLUE,    -1)  # CYAN

        return {
            "RED":   curses.color_pair(1) | curses.A_BOLD,
            "DIM":   curses.color_pair(2) | curses.A_DIM,
            "NORM":  curses.color_pair(3),
            "LABEL": curses.color_pair(4) | curses.A_BOLD,
            "GREEN": curses.color_pair(5) | curses.A_BOLD,
            "HINT":  curses.color_pair(6),
            "CYAN":  curses.color_pair(7) | curses.A_BOLD,
        }
