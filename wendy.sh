#!/bin/bash

# ─────────────────────────────────────────
#  WENDY - Aerospace Scene Launcher
# ─────────────────────────────────────────

YOUTUBE_URL="https://www.youtube.com/watch?v=BN1WwnEDWAM&list=RDBN1WwnEDWAM&start_radio=1"

echo "🤖 Wendy: Setting up workspace 1..."

# Switch to workspace 1
aerospace workspace 1

# Open Cursor, Terminal, and Finder
open -a "Cursor"
sleep 0.5
open -a "Terminal"
sleep 0.5
open -a "Finder"

echo "🤖 Wendy: Switching to workspace 9 for YouTube..."
sleep 1

# Switch to workspace 9
aerospace workspace 9

# Open YouTube video in Firefox
open -a "Firefox" "$YOUTUBE_URL"

echo "✅ Wendy: All done!"
