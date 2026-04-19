#!/usr/bin/env python3
"""Load and print configuration/settings.json (normalized via settings_store)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
_CFG = ROOT / "configuration"
if str(_CFG) not in sys.path:
    sys.path.insert(0, str(_CFG))

from config.settings_store import SETTINGS_PATH, load_settings  # noqa: E402

SECTIONS = ("apps", "states", "layout_catalog", "color_mode")


def load_raw_file(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"Missing {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    return raw if isinstance(raw, dict) else {}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Print configuration/settings.json. "
            "Default load matches the TUI (normalized, including layout_catalog merge)."
        )
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the Enter prompt",
    )
    parser.add_argument(
        "-s",
        "--section",
        choices=("all",) + SECTIONS,
        default="all",
        help="Print only one top-level key (default: all)",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Read JSON from disk without normalizing (no layout_catalog default merge)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Single-line JSON (good for piping)",
    )
    parser.add_argument(
        "--path",
        type=Path,
        metavar="FILE",
        help=f"Settings file to read (default: {SETTINGS_PATH})",
    )
    args = parser.parse_args()

    path = args.path.resolve() if args.path else SETTINGS_PATH

    if not args.yes:
        input(f"Press Enter to load {path}… ")

    try:
        if args.raw or args.path:
            data = load_raw_file(path)
        else:
            data = load_settings()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    if args.section != "all":
        data = data.get(args.section, "" if args.section == "color_mode" else {})

    indent = None if args.compact else 2
    print(json.dumps(data, indent=indent, ensure_ascii=False))


if __name__ == "__main__":
    main()
