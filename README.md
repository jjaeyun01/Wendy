# 🤖 Wendy
> Your personal Jarvis — clap twice, and Wendy sets up your entire workspace automatically.

---

## What is Wendy?

Wendy is a Mac automation assistant that watches for two claps via your webcam and instantly launches your development environment. It opens Cursor, Terminal, and Finder on your first Aerospace workspace, and plays a YouTube video on a second workspace — all hands-free.

---

## Project Structure

```
wendy/
├── main.sh                  # Entry point — orchestrates everything
├── config.json              # Settings: YouTube URL, workspace IDs, app names
│
├── listeners/
│   └── clap_detector.py     # Webcam input → detects 2 claps → triggers main.sh
│
├── scenes/
│   ├── workspace1.sh        # Opens Cursor, Terminal, and Finder on space 1
│   └── workspace2.sh        # Opens YouTube video on space 2
│
├── utils/
│   ├── aerospace.sh         # Aerospace workspace helper functions
│   └── notify.sh            # macOS notifications for Wendy feedback
│
└── requirements.txt         # Python dependencies
```

---

## How It Works

```
Webcam
   └── clap_detector.py
         └── sees 2 claps
               └── main.sh
                     ├── workspace1.sh → Cursor + Terminal + Finder
                     └── workspace2.sh → YouTube video
```

---

## Trigger Options

Wendy is triggered by a **double clap** detected via your Mac's webcam using hand gesture recognition. MediaPipe tracks both hands in real time and detects when they come together twice within ~0.8 seconds.

A **keyboard hotkey fallback** is also recommended for low-light environments.

| Method | Pros | Cons |
|---|---|---|
| 📷 Webcam / Clap Detection | Hands-free, cool factor | Needs decent lighting |
| ⌨️ Hotkey | Reliable, zero false positives | Less hands-free |
| 🖱️ Mouse Gesture | No accidental triggers | Must be at desk |
| 📱 iPhone Shortcut | Works from across the room | Extra setup required |
| ⌚ Apple Watch tap | Wrist-based, very Jarvis | Needs Watch + Shortcuts |

**Recommended:** Clap detection as primary + hotkey as fallback.

---

## Tech Stack

- **Shell (Bash)** — workspace launching and app control
- **Python** — clap detection via webcam and hand gesture recognition
- **Aerospace** — macOS tiling window manager for workspace switching
- `mediapipe` — real-time hand landmark detection
- `opencv-python` — webcam stream processing
- `numpy` — coordinate distance calculation

---

## Setup

### 1. Install dependencies

```bash
pip install mediapipe opencv-python numpy
```

### 2. Make scripts executable

```bash
chmod +x main.sh scenes/workspace1.sh scenes/workspace2.sh
```

### 3. Configure Wendy

Edit `config.json` to set your YouTube URL and workspace IDs:

```json
{
  "youtube_url": "https://www.youtube.com/watch?v=YOUR_VIDEO",
  "workspace_dev": 1,
  "workspace_media": 2
}
```

### 4. Grant camera permission

Make sure your terminal app has camera access:
**System Settings → Privacy & Security → Camera → enable for Terminal**

### 5. Run Wendy

```bash
python listeners/clap_detector.py
```

Then clap twice in front of your webcam — Wendy will handle the rest.

---

## Requirements

- macOS
- [Aerospace](https://github.com/nikitabobko/AeroSpace) window manager installed and configured
- Cursor, Terminal, Finder (standard macOS apps)
- Python 3.8+
- `aerospace` CLI available in your PATH (check with `which aerospace`)
- Webcam (built-in or external)

---

## License

MIT
