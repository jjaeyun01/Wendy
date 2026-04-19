"""Shared display helpers for layout pickers (layout1–layout4, layout3)."""


def cat_label(key: str) -> str:
    return {
        "browser": "Browser",
        "ide": "IDE",
        "music": "Music",
        "notes": "Notes",
        "terminal": "Terminal",
    }.get(key, key.replace("_", " ").title())
