# Wendy

> macOS workspace helper: double-clap to launch your dev stack, or drive everything from a small terminal config UI.

---

## What is Wendy?

Wendy ties together three pieces:

1. **Config TUI** (`python3 main.py`) — pick **color mode**, default **apps** per category (browser, IDE, music, notes, terminal), and **States** (named presets with per-workspace contents and tile layouts). Settings persist in `settings.json` beside the repo.
2. **Clap detector** (`clap_detector.py`) — listens for two claps and runs `wendy.sh`.
3. **Launcher** (`wendy.sh`) — reads `settings.json`, switches [Aerospace](https://github.com/nikitabobko/AeroSpace) workspaces, and `open`s your apps plus a YouTube URL in the browser.

---

## Project structure

```
Wendy/
├── main.py                 # Config TUI entry (curses menu)
├── clap_detector.py        # Mic → two claps → invokes wendy.sh
├── wendy.sh                # Bash: parse JSON, aerospace + open apps / YouTube
├── settings.json           # Repo root; written by the TUI (see below)
├── requirements.txt        # sounddevice, numpy (clap detector)
│
├── config/
│   ├── apps.py             # Pick default app per category; scans macOS app folders
│   ├── colormode.py        # Light / dark
│   ├── colorpicker.py      # First-run color mode
│   ├── layout.py           # Tile layout pickers + A/B/C/D slot assignment
│   ├── palette.py          # Terminal colors
│   ├── settings_store.py   # Path to settings.json, normalize + save
│   └── states.py           # States → workspaces → Contents + Layouts
│
└── documentation/          # Notes per module (optional reading)
```

`wendy.sh` calls `splash.py` on startup if you add that script next to it; the repo may ship without it—create a no-op splash or remove the line in `wendy.sh` if you do not need it.

---

## How it works

```
Microphone
   └── clap_detector.py
         └── two claps within the window
               └── wendy.sh
                     ├── reads settings.json
                     ├── workspace_dev → open IDE, terminal, notes, …
                     └── workspace_media → browser + YouTube URL
```

Use a **keyboard hotkey** or other trigger to call `wendy.sh` directly if claps are unreliable.

---

## Configuration (`settings.json`)

The **config TUI** saves a **canonical** shape via `config/settings_store.py`:

```json
{
  "color_mode": "dark",
  "apps": {
    "browser": "",
    "ide": "",
    "music": "",
    "notes": "",
    "terminal": ""
  },
  "states": {}
}
```

- **`apps`** — default `.app` names per category (chosen from apps discovered under `/Applications`, `/System/Applications`, `/System/Applications/Utilities`, and `~/Applications` on macOS).
- **`states`** — optional named presets. Each state has **`workspaces`**: keys like `"1"` … `"9"` / `"A"`…`"Z"`. Each workspace can include:
  - **`apps`** — subset of contents (browser, ide, music, notes, terminal)
  - **`browser_url`**, **`music_url`** — optional URLs when browser/music is in use
  - **`layout`** — after you use **States → … → Layouts**: `{ "n": 1–4, "id": <tile id>, "slots": { "A": "browser", … } }` (slots for multi-pane layouts)

**Launcher extras:** `wendy.sh` still reads **optional** top-level keys if present (for example `youtube_url`, `workspace_dev`, `workspace_media`, `trigger`). Those are **not** rewritten by the TUI’s `save_settings`; add them by hand if you use the shell launcher’s YouTube/workspace behavior.

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Make the launcher executable

```bash
chmod +x wendy.sh
```

### 3. Configure Wendy

```bash
python3 main.py
```

Use **Apps**, **Color Mode**, and **States**. Press **Esc** where indicated to save. This writes `settings.json` in the repo root.

### 4. Microphone (for clap detection)

**System Settings → Privacy & Security → Microphone** — enable for the terminal (or IDE) you use to run `clap_detector.py`.

### 5. Run the clap detector

From the repo root:

```bash
python3 clap_detector.py
```

Ensure `wendy.sh` is executable and on the expected path (the detector typically invokes it from the project directory—check `clap_detector.py` if you move files).

---

## Clap detector tuning

Edit constants in `clap_detector.py` (e.g. threshold, window between claps, cooldown) if Wendy triggers too often or misses claps.

---

## Requirements

- macOS (app discovery and `open -a` are built for Apple’s layout)
- [AeroSpace](https://github.com/nikitabobko/AeroSpace) installed with `aerospace` on your `PATH`
- Python 3.10+ recommended (project uses modern typing)
- Packages: `sounddevice`, `numpy` (see `requirements.txt`)

---

## License

MIT
