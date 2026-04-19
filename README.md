# 🤖 Wendy

> Your personal Jarvis — clap twice, and Wendy sets up your entire workspace automatically.

---

## What is Wendy?

Wendy is a Mac automation assistant that listens for two claps via your microphone and instantly launches your development environment. It opens your chosen apps on your dev Aerospace workspace, and plays a YouTube video in your browser on a second workspace — all hands-free. Everything is configured via a `settings.json` file.

---

## Project Structure

```
wendy/
├── main.py                  # Entry point — launches the config TUI
├── splash.py                # Terminal splash screen shown on startup
├── wendy.sh                 # Reads settings.json and launches everything
├── settings.json            # Generated config: YouTube URL, workspaces, apps, browser
├── requirements.txt         # Python dependencies
│
├── config/                  # Config TUI — all configuration screens
│   ├── __init__.py
│   ├── apps.py              # Assign default apps per category
│   ├── colormode.py         # Switch light / dark mode
│   ├── colorpicker.py       # Initial color mode picker on first launch
│   ├── palette.py           # Color definitions — single source of truth
│   └── states.py            # Manage named workspace states
│
├── listeners/
│   └── clap_detector.py     # Mic input → detects 2 claps → triggers wendy.sh
│
├── scenes/
│   ├── workspace1.sh        # Opens dev apps on workspace 1
│   └── workspace9.sh        # Opens YouTube in Firefox on workspace 9
│
└── utils/
    ├── aerospace.sh         # Aerospace workspace helper functions
    └── notify.sh            # macOS notifications for Wendy feedback
```

---

## How It Works

```
Microphone
   └── clap_detector.py
         └── hears 2 claps
               └── wendy.sh
                     ├── reads settings.json
                     ├── shows splash.py
                     ├── workspace 1 → Cursor + Terminal + Finder
                     └── workspace 9 → YouTube in Firefox
```

---

## Trigger Options

Wendy is triggered by a **double clap** detected via your Mac's microphone. The clap detector listens for two short loud audio spikes within ~1.2 seconds of each other, with debouncing and a cooldown to prevent false triggers.

A **keyboard hotkey fallback** is also recommended for noisy environments.

| Method | Pros | Cons |
|---|---|---|
| 🎤 Mic / Clap Detection | Hands-free, cool factor | Can false-trigger in noisy rooms |
| ⌨️ Hotkey | Reliable, zero false positives | Less hands-free |
| 🖱️ Mouse Gesture | No accidental triggers | Must be at desk |
| 📱 iPhone Shortcut | Works from across the room | Extra setup required |
| ⌚ Apple Watch tap | Wrist-based, very Jarvis | Needs Watch + Shortcuts |

**Recommended:** Clap detection as primary + hotkey as fallback.

---

## Tech Stack

- **Shell (Bash)** — workspace launching and app control
- **Python** — config TUI, splash screen, and clap/audio detection via microphone
- **Aerospace** — macOS tiling window manager for workspace switching
- `curses` — terminal UI for the config screens
- `sounddevice` — real-time microphone input
- `numpy` — audio amplitude spike detection

---

## Configuration

Wendy reads all settings from `settings.json` at launch. Generate this file using the config TUI (`python3 main.py`), or edit it manually:

```json
{
  "color_mode": "dark",
  "browser": "Firefox",
  "youtube_url": "https://www.youtube.com/watch?v=BN1WwnEDWAM&list=RDBN1WwnEDWAM&start_radio=1",
  "workspace_dev": 1,
  "workspace_media": 9,
  "apps": {
    "browser": "Firefox",
    "ide": "Cursor",
    "music": "Spotify",
    "notes": "Obsidian",
    "terminal": "Ghostty"
  },
  "states": {},
  "trigger": "clap"
}
```

| Key | Description |
|---|---|
| `color_mode` | `dark` or `light` — set via the config TUI |
| `youtube_url` | The YouTube link to open on launch |
| `browser` | Browser app name (Firefox, Safari, Arc, etc.) |
| `workspace_dev` | Aerospace workspace number for dev apps |
| `workspace_media` | Aerospace workspace number for YouTube |
| `apps` | Default app per category, set via the config TUI |
| `states` | Named workspace states (triggers and actions TBD) |
| `trigger` | `clap`, `hotkey`, or `both` |

---

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Make scripts executable

```bash
chmod +x wendy.sh scenes/workspace1.sh scenes/workspace9.sh
```

### 3. Configure Wendy

```bash
python3 main.py
```

This launches the config TUI where you can set your color mode, default apps, and workspace states. Settings are saved to `settings.json`.

### 4. Grant microphone permission

Make sure your terminal app has microphone access:

**System Settings → Privacy & Security → Microphone → enable for Terminal**

### 5. Run Wendy

```bash
python3 listeners/clap_detector.py
```

Then clap twice — Wendy will show the splash screen and handle the rest.

---

## Clap Detector Settings

You can tune the detector in `listeners/clap_detector.py`:

| Variable | Default | Description |
|---|---|---|
| `THRESHOLD` | `0.25` | Amplitude level to count as a clap (0.0–1.0) |
| `CLAP_WINDOW` | `1.2s` | Max time between clap 1 and clap 2 |
| `COOLDOWN` | `3.0s` | Ignore period after a successful trigger |

If Wendy triggers too easily, raise `THRESHOLD`. If she misses claps, lower it.

---

## Requirements

- macOS
- [Aerospace](https://github.com/nikitabobko/AeroSpace) window manager installed and configured
- `aerospace` CLI available in your PATH (check with `which aerospace`)
- Python 3.8+
- Cursor, Terminal, Finder (or any apps listed in `settings.json`)

---

## License

MIT
