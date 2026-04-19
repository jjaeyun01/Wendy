# Wendy

> Say her name. Clap twice. Your entire workspace appears.

Wendy is a macOS automation assistant inspired by Jarvis. She listens for her name, waits for a double clap confirmed by your camera, then instantly launches your development environment — music, IDE, terminal, and file manager — all hands-free.

---

## Demo

```
You: "Hey Wendy"
  🎤 Wake word detected — armed for 10s

You: *clap clap*
  👁  Visual clap detected
  ⬤  Clap 1  ⬤  Clap 2
  ✦  Launching workspace...

Result:
  Workspace Q  →  Cursor (left) | Finder (top right) / Terminal (bottom right)
  Workspace 9  →  YouTube music in Firefox
```

---

## How It Works

```
wake_word.py        — Vosk (offline STT) listens for "Wendy"
      ↓ armed
clap_detector.py    — mic + camera, both must confirm
      ├── 🔊 Audio:  CNN on Mel spectrogram  (falls back to FFT if no model)
      └── 👁  Vision: frame-differencing, two hands converging
                    ↓ double clap confirmed
state_runner.py     — switches workspaces, opens apps, arranges windows
```

### Three-layer trigger

| Layer | Technology | Purpose |
|---|---|---|
| Wake word | Vosk offline STT | Activates listening — only responds after "Wendy" |
| Audio clap | CNN + Mel spectrogram | Distinguishes real claps from voice and noise |
| Visual clap | OpenCV frame differencing | Ensures hands are actually clapping, not ambient noise |

All three must align within a time window to fire. This virtually eliminates false triggers.

---

## Project Structure

```
Wendy/
├── wendy_daemon.py          # Main entry point — wires everything together
├── wake_word.py             # "Wendy" wake word detection (Vosk)
├── clap_detector.py         # Mic + camera double-clap detection
├── state_runner.py          # Workspace launcher (Aerospace)
├── config.json              # All tuneable settings
│
├── ml/                      # CNN clap classifier
│   ├── mel.py               # Pure-numpy Mel spectrogram
│   ├── clap_cnn.py          # Model architecture + real-time inference
│   ├── collect.py           # Record training samples (clap / noise)
│   ├── train.py             # Train the CNN
│   ├── test.py              # Live test the trained model
│   └── models/              # Saved model weights (.pt)
│
├── triggers/                # Extensible gesture trigger system
│   ├── base.py              # GestureTrigger ABC + GestureEngine
│   ├── dtw.py               # DTW matching + CLI recorder
│   ├── audio_dtw.py         # MFCC-based audio DTW trigger
│   └── templates/           # Saved gesture templates (.json)
│
└── listeners/
    ├── motion_detector.py   # MediaPipe gesture recorder/matcher
    └── motion_features.py   # Hand landmark feature extraction
```

---

## Requirements

- macOS (Apple Silicon or Intel)
- Python 3.11+ (Python 3.13 supported — mediapipe excluded)
- [AeroSpace](https://github.com/nikitabobko/AeroSpace) window manager

---

## Installation

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
pip install torch
```

### 2. Download Vosk speech model

```bash
# Download and unzip into the repo root
# https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.22.zip
# Result: Wendy/vosk-model-small-en-us-0.22/
```

### 3. Grant permissions

**System Settings → Privacy & Security**

| Permission | Required by |
|---|---|
| Microphone | wake word + clap detection |
| Camera | visual clap detection |
| Accessibility | AeroSpace window arrangement |

### 4. Configure workspaces

Edit `config.json` to set your AeroSpace workspace names, apps, and YouTube URL:

```json
{
  "profiles": [
    {
      "id": "dev-mode",
      "workspace": "Q",
      "layout": {
        "relocatable_apps": [
          { "bundle_id": "com.todesktop.230313mzl4w4u92", "open_cmd": "open -n /Applications/Cursor.app" },
          { "bundle_id": "com.apple.Terminal",             "open_cmd": "open -n /System/Applications/Utilities/Terminal.app" },
          { "bundle_id": "com.apple.finder",               "open_cmd": "open -a Finder" }
        ]
      }
    },
    {
      "id": "jarvis-mode",
      "workspace": "9",
      "music": {
        "youtube_url": "https://www.youtube.com/watch?v=BN1WwnEDWAM",
        "player": "firefox"
      }
    }
  ]
}
```

---

## Running Wendy

```bash
python3 wendy_daemon.py
```

### Usage

1. Say **"Wendy"** (or "Hey Wendy")
2. Within 10 seconds, **clap twice** in front of your camera
3. Watch your workspace assemble itself

---

## CNN Clap Classifier

A pre-trained model is included in `ml/models/`. If you want to retrain it for your own microphone and environment:

```bash
# 1. Record clap samples (~30 minimum)
python3 ml/collect.py clap
# Press SPACE to record each sample, Q to finish

# 2. Record noise samples (voice, typing, ambient sounds)
python3 ml/collect.py noise

# 3. Train
python3 ml/train.py

# 4. Test live
python3 ml/test.py
```

The daemon automatically loads the most recently trained model. If no model is found, it falls back to FFT-based spectral detection.

---

## Custom Gesture Triggers (DTW)

Add your own sound gestures without writing a new model:

```bash
# Record a finger-snap trigger (5 samples)
python3 triggers/dtw.py record snap

# See all saved triggers
python3 triggers/dtw.py list

# Test live
python3 triggers/dtw.py test snap
```

Templates are saved to `triggers/templates/<name>.json`. Use in code:

```python
from triggers.audio_dtw import AudioDTWTrigger

snap = AudioDTWTrigger.from_file("snap", action=lambda: print("snapped!"))
# call snap.detect(audio_block) inside your audio callback
```

---

## Tuning

All settings are in `config.json` under `"settings"`:

| Key | Default | Description |
|---|---|---|
| `clap_threshold` | `0.05` | Minimum amplitude to consider as a clap |
| `clap_interval_ms` | `1500` | Max gap between clap 1 and clap 2 (ms) |
| `post_trigger_guard_sec` | `25` | Deaf period after a successful trigger |
| `visual_clap_require` | `true` | Require camera confirmation |
| `visual_clap_distance` | `0.30` | How close hands must come (normalized) |
| `visual_clap_window_sec` | `1.5` | Time window to match audio + visual |
| `wake_word.word` | `"wendy"` | Wake word |
| `wake_word.arm_seconds` | `10` | How long to listen after wake word |
| `youtube_settle_sec` | `3` | Wait time after opening YouTube |

---

## Tech Stack

| Component | Technology |
|---|---|
| Wake word | [Vosk](https://alphacephei.com/vosk/) offline STT |
| Audio clap (CNN) | PyTorch · Mel spectrogram (pure numpy) |
| Audio clap (fallback) | FFT spectral energy ratio |
| Visual clap | OpenCV frame differencing |
| Custom gestures | DTW (pure numpy) + MFCC |
| Window management | [AeroSpace](https://github.com/nikitabobko/AeroSpace) |

---

## License

MIT
