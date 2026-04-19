#!/usr/bin/env python3
"""Load and print configuration/settings.json after a prompt (or use -y to skip)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = ROOT / "configuration" / "settings.json"


def load_settings() -> dict:
    if not SETTINGS_PATH.is_file():
        raise FileNotFoundError(f"Missing {SETTINGS_PATH}")
    return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Print contents of configuration/settings.json"
    )
    parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip the prompt and print immediately (for scripts)",
    )
    args = parser.parse_args()

    if not args.yes:
        input("Press Enter to load settings.json… ")

    try:
        data = load_settings()
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
