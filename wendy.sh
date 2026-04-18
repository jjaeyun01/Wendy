#!/bin/bash

# ─────────────────────────────────────────
#  WENDY - Aerospace Scene Launcher
#  Workspace 1 layout mirrors config.json → profiles → dev-mode → layout.arrange
# ─────────────────────────────────────────

YOUTUBE_URL="https://www.youtube.com/watch?v=BN1WwnEDWAM&list=RDBN1WwnEDWAM&start_radio=1"

# Bundle IDs (same as dev-mode in config.json)
CURSOR_BUNDLE="com.todesktop.230313mzl4w4u92"
TERMINAL_BUNDLE="com.apple.Terminal"
FINDER_BUNDLE="com.apple.finder"

# Seconds between launching apps (windows need time before arrange)
APP_LAUNCH_GAP="0.8"
PRE_ARRANGE_PAUSE="1"

focus_first_window_in_ws1() {
  local bundle_id="$1"
  local attempt=0
  local max=30
  local wid

  while (( attempt < max )); do
    wid=$(aerospace list-windows --workspace 1 --app-bundle-id "$bundle_id" --json 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    if data:
        print(data[0]['window-id'], end='')
except Exception:
    pass
")
    if [[ -n "$wid" ]]; then
      aerospace focus --window-id "$wid"
      return 0
    fi
    sleep 0.2
    ((attempt++))
  done

  echo "⚠️  Wendy: no window found for $bundle_id on workspace 1" >&2
  return 1
}

arrange_dev_workspace() {
  # Layout: Cursor (left) | Finder (top right) / Terminal (bottom right)
  focus_first_window_in_ws1 "$CURSOR_BUNDLE" || return 1
  aerospace layout h_tiles
  aerospace move left; aerospace move left   # push Cursor to far left

  focus_first_window_in_ws1 "$TERMINAL_BUNDLE" || return 1
  aerospace move right; aerospace move right  # push Terminal to far right

  # Now order is [Cursor | Finder | Terminal]
  # Terminal joins Finder → sub-container [Finder | Terminal]
  aerospace join-with left
  # Stack vertically: Finder on top, Terminal on bottom
  aerospace layout v_tiles
}

echo "🤖 Wendy: Starting YouTube on workspace 9..."
aerospace workspace 9
open -a "Firefox" "$YOUTUBE_URL"

echo "🤖 Wendy: Setting up workspace 1..."
aerospace workspace 1

open -n /Applications/Cursor.app
sleep "$APP_LAUNCH_GAP"
open -n /System/Applications/Utilities/Terminal.app
sleep "$APP_LAUNCH_GAP"
# Finder is always running; open a fresh window via AppleScript
osascript -e 'tell application "Finder" to make new Finder window'
sleep "$APP_LAUNCH_GAP"

echo "🤖 Wendy: Arranging windows..."
sleep "$PRE_ARRANGE_PAUSE"
arrange_dev_workspace

echo "✅ Wendy: All done!"
