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

# ── Parse settings.json ─────────────────
parse() {
  python3 -c "import json,sys; d=json.load(open('$SETTINGS')); print($1)"
}

YOUTUBE_URL=$(parse "d['youtube_url']")
BROWSER=$(parse "d['browser']")
WS_DEV=$(parse "d['workspace_dev']")
WS_MEDIA=$(parse "d['workspace_media']")
TRIGGER=$(parse "d['trigger']")
APPS=$(parse "' '.join(d['apps'])")

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
