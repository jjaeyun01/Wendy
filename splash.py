import os
import re
import shutil
import sys

RED = "\033[38;2;180;50;50m"
CYAN = "\033[38;2;80;180;160m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def draw_splash():
    w = shutil.get_terminal_size().columns
    inner_w = w - 2

    top = "╭" + "─" * inner_w + "╮"
    bottom = "╰" + "─" * inner_w + "╯"

    def row(text=""):
        visible = re.sub(r"\033\[[^m]*m", "", text)
        pad = " " * (inner_w - len(visible))
        print(f"{RED}{BOLD}│{RESET}{text}{pad}{RED}{BOLD}│{RESET}")

    print()
    print(f"{RED}{BOLD}{top}{RESET}")
    row()
    row(f"  {RED}{BOLD}Wendy{RESET}")
    row(f"  {DIM}v0.1.0{RESET}")
    row()
    row(f"  {DIM}This script opens apps from settings.json.{RESET}")
    row(f"  {DIM}It does not use the microphone.{RESET}")
    row()
    row(f"  {CYAN}⬤  Hands-free clap:{RESET}  {DIM}python3 wendy_daemon.py{RESET}")
    row()
    print(f"{RED}{BOLD}{bottom}{RESET}")
    print()


def wait_splash_continue() -> None:
    """Block until Enter — optional skip for automation or non-interactive shells."""
    if os.environ.get("WENDY_SKIP_SPLASH_WAIT", "").strip() in ("1", "true", "yes"):
        return
    if not sys.stdin.isatty():
        return
    try:
        input(f"  {DIM}Press Enter to open workspace (settings.json)...{RESET}\n")
    except EOFError:
        pass


if __name__ == "__main__":
    draw_splash()
    wait_splash_continue()
