#!/bin/bash

# ─────────────────────────────────────────
#  WENDY - Workspace Launcher
#  Reads settings from settings.json
# ─────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SETTINGS="$SCRIPT_DIR/settings.json"

# ── Show splash screen ──────────────────
python3 "$SCRIPT_DIR/splash.py"

# ── Check settings.json exists ──────────
if [ ! -f "$SETTINGS" ]; then
  echo "  ✗ settings.json not found. Run the config screen first."
  exit 1
fi

# ── Parse settings.json (nested apps + optional legacy keys) ─────────────────
export WENDY_SETTINGS="$SETTINGS"
eval "$(python3 <<'PY'
import json
import os
from pathlib import Path

def sh_single(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"

path = Path(os.environ["WENDY_SETTINGS"])
raw = json.loads(path.read_text())

youtube_url = raw.get("youtube_url") or "https://www.youtube.com/watch?v=BN1WwnEDWAM&list=RDBN1WwnEDWAM&start_radio=1"
workspace_dev = raw.get("workspace_dev", 1)
workspace_media = raw.get("workspace_media", 9)
trigger = raw.get("trigger", "clap")

apps = raw.get("apps")
browser = "Safari"
dev_names: list[str] = []

if isinstance(apps, list):
    dev_names = [str(a) for a in apps if a]
    browser = str(raw.get("browser", browser))
elif isinstance(apps, dict):
    browser = str(apps.get("browser") or raw.get("browser", browser))
    for key in ("ide", "terminal", "notes", "music"):
        v = apps.get(key)
        if isinstance(v, str) and v.strip():
            dev_names.append(v.strip())
else:
    browser = str(raw.get("browser", browser))

print(f"YOUTUBE_URL={sh_single(youtube_url)}")
print(f"BROWSER={sh_single(browser)}")
print(f"WS_DEV={workspace_dev!s}")
print(f"WS_MEDIA={workspace_media!s}")
print(f"TRIGGER={sh_single(trigger)}")
print(f"APPS={sh_single(' '.join(dev_names))}")
PY
)"

echo "  ✦ Wendy is starting up..."
echo "  ✦ Dev workspace  → $WS_DEV"
echo "  ✦ Media workspace → $WS_MEDIA"
echo "  ✦ Browser        → $BROWSER"
echo "  ✦ Trigger        → $TRIGGER"
echo ""

# ── Workspace 1: Dev apps ───────────────
echo "  ⬤  Switching to workspace $WS_DEV..."
aerospace workspace "$WS_DEV"
sleep 0.5

for APP in $APPS; do
  echo "  ⬤  Opening $APP..."
  open -a "$APP"
  sleep 0.5
done

# ── Workspace media: YouTube ────────────
echo ""
echo "  ⬤  Switching to workspace $WS_MEDIA..."
sleep 1
aerospace workspace "$WS_MEDIA"

echo "  ⬤  Opening $BROWSER → YouTube..."
open -a "$BROWSER" "$YOUTUBE_URL"

echo ""
echo "  ✓  Wendy is all set. Good luck."
echo ""
