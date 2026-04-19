# Wendy

> macOS workspace automation with a JARVIS-style control panel: optional offline wake word (“Wendy”), double-clap (plus optional on-camera hand clap), and [AeroSpace](https://github.com/nikitabobko/AeroSpace)-driven profiles defined in `config.json`.

---

## What is Wendy?

1. **Wendy App** (`wendy_app.py`) — PyQt6 “reactor” UI: status for camera / mic / wake word, live mic level and waveform, trigger cards (built-in double-clap + DTW templates from `triggers/templates/`), daemon log, **Start / Stop** for the background listener. On launch it briefly waits then **auto-starts** the daemon (you can stop it from the footer).
2. **Daemon** (`wendy_daemon.py`) — loads optional **Vosk** wake word from `config.json`, then runs **`clap_detector.run_forever`**: mic (and optional **OpenCV** visual clap + **CNN** spectral gate from `ml/`) → on success runs **`state_runner.py`** to apply the next profile in your trigger sequence.
3. **State runner** (`state_runner.py`) — reads **`config.json`**: switches AeroSpace workspace, runs `commands`, opens apps, optional **music / YouTube** flows, and runs **`arrange`** steps.

---

## How it fits together

```
config.json (profiles + trigger + settings)
        │
        ▼
wendy_app.py  ──starts──►  wendy_daemon.py
                               │
                               ├── wake_word.py (Vosk, optional)
                               └── clap_detector.py
                                       ├── optional VisualClapDetector (camera)
                                       ├── optional ClapCNNClassifier (ml/)
                                       └── subprocess → state_runner.py
                                                            └── aerospace, open, …
```

Use **Wendy App** for day-to-day control; run **`python3 wendy_daemon.py`** alone if you do not need the UI.

---

## Project layout

```
Wendy/
├── wendy_app.py           # PyQt6 control panel (run this for the “app”)
├── wendy_daemon.py        # Wake word + clap loop; LaunchAgent installer flags
├── clap_detector.py       # Audio (+ optional visual) double-clap → state_runner
├── state_runner.py        # Apply profiles from config.json (AeroSpace + apps)
├── wake_word.py           # Vosk wake word → “arm” window for claps
├── config.json            # Single source of truth: settings, profiles, trigger
│
├── triggers/              # DTW gesture triggers (templates/*.json)
├── ml/                    # Optional clap CNN (train/load; see ml/)
├── listeners/             # Motion helpers (used by broader experiments)
│
├── requirements.txt       # sounddevice, numpy, opencv-python, vosk, torch, PyQt6
│
└── archive/               # Legacy stack (curses TUI, settings.json, wendy.sh, …)
    ├── main_tui.py        # Old config TUI (was conceptually “main.py”)
    ├── wendy.sh           # Bash launcher for settings.json-era flow
    └── config/            # TUI modules + documentation
```

---

## Configuration (`config.json`)

Everything important lives at the repo root in **`config.json`**.

- **`settings`** — Clap thresholds and timing (`clap_threshold`, `clap_interval_ms`, `cooldown_ms`, …), optional **`visual_clap_require`** / **`visual_clap_window_sec`** / **`visual_clap_distance`** / **`camera_index`**, delays for **`state_runner`** (`apply_command_delay_sec`, …), and **`wake_word`** (`enabled`, `word`, `aliases`, `arm_seconds`).
- **`profiles`** — List of workspace presets. Each profile typically has **`id`**, **`name`**, **`workspace`**, optional **`icon`**, **`layout`** with **`commands`**, **`relocatable_apps`**, **`arrange`** (AeroSpace CLI lines), and optional **`music`** (e.g. `youtube_url`, `player`, local `path`).
- **`trigger`** — e.g. **`type`**: `double_clap`, **`target_profiles`**: ordered list of profile `id`s to rotate through on each successful trigger (or **`target_profile`** for a single id).

Edit **`config.json`** in your editor; the app does not yet ship a full visual profile editor.

---

## Setup

### 1. Python dependencies

```bash
cd /path/to/Wendy
pip install -r requirements.txt
```

`requirements.txt` pins **PyQt6**, **sounddevice**, **numpy**, **opencv-python**, **vosk**, and **torch** for the full stack. **MediaPipe** is commented out (Python 3.13 compatibility); use Python ≤3.12 if you need it elsewhere.

### 2. AeroSpace

Install [AeroSpace](https://github.com/nikitabobko/AeroSpace) and ensure **`aerospace`** is on your `PATH`.

### 3. Wake word (optional)

1. Enable and tune **`settings.wake_word`** in **`config.json`**.
2. Download a Vosk model (e.g. [small English](https://alphacephei.com/vosk/models)) and unzip it **inside the repo root** so a folder like `vosk-model-small-en-us-0.22/` exists next to `wake_word.py`.

If the model is missing or mic init fails, the daemon prints that **clap detection stays always active** (no “Wendy” gate).

### 4. macOS privacy

- **Microphone** — for Terminal, your IDE, or `python3` host running Wendy.
- **Camera** — if **`visual_clap_require`** is true (default in many setups), for the visual hand-clap path in **`clap_detector.py`**.
- **Accessibility** — may be needed for optional automation (e.g. Firefox playback helper paths in **`state_runner.py`**).

### 5. Run the app

```bash
python3 wendy_app.py
```

### 6. Run the daemon only (no UI)

```bash
python3 wendy_daemon.py
```

### 7. Login item / auto-restart (optional)

```bash
python3 wendy_daemon.py --install-launchagent
launchctl load ~/Library/LaunchAgents/com.wendy.daemon.plist
```

Uninstall: `launchctl unload …` then remove the plist (see docstring at top of **`wendy_daemon.py`**).

---

## Clap detector notes

- With **`visual_clap_require`: true**, a **mic double-clap** and a **visual “clap”** (hands coming together on camera) must align within **`visual_clap_window_sec`** to reduce false triggers from speakers or room noise.
- An optional **CNN** classifier under **`ml/`** loads lazily when available to add a spectral gate (see console for `Clap CNN loaded`).
- On fire, **`clap_detector.py`** spawns **`state_runner.py`** with the repo as cwd (same as manual `python3 state_runner.py` for testing).

Tune values under **`config.json` → `settings`**.

---

## Custom audio triggers (DTW)

Record templates with:

```bash
python3 triggers/dtw.py record <name>
```

Templates are stored under **`triggers/templates/<name>.json`**. Use **↺ REFRESH** in Wendy App to pick up new files. The built-in **CLAP × 2** card stays separate from DTW templates.

---

## Legacy: curses TUI + `wendy.sh` + `settings.json`

The older flow (curses menu writing **`settings.json`**, **`wendy.sh`** reading it) lives under **`archive/`** (`main_tui.py`, **`archive/wendy.sh`**, **`archive/config/`**, …). New development targets **`config.json`** + **`wendy_app.py`** + **`state_runner.py`**.

---

## Requirements

- **macOS** (paths, `open`, AeroSpace integration)
- **Python 3.10+** recommended (3.13 ok for current `requirements.txt`; avoid uncommented mediapipe on 3.13)
- **AeroSpace** on `PATH`
- Packages: see **`requirements.txt`**

---

## License

MIT
