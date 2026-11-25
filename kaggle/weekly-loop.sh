#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Master launcher for the weekly Gen 5 loop.
# Run this every Saturday: it trains, launches self-play fleet, tracks Elo.
#
# Usage: bash kaggle/weekly-loop.sh [train|fleet|retrain|track|all]
#   train   - GPU training (h1024 full data)
#   fleet   - CPU self-play fleet (20 workers)
#   retrain - Weekly retrain on all data
#   track   - Track Elo from latest panel
#   all     - Run train -> fleet -> track (default)

set -euo pipefail
cd "$(dirname "$0")/.."

MODE=${1:-all}
WEEK=$(date -u +%Y-W%V)

case "$MODE" in
    train)
        say "=== SATURDAY GPU TRAIN: h1024 full data ==="
        bash kaggle/launch-train-g5-h1024.sh
        ;;
    fleet)
        say "=== CPU SELF-PLAY FLEET ==="
        bash kaggle/selfplay-fleet.sh
        ;;
    retrain)
        say "=== WEEKLY RETRAIN ON ALL DATA ==="
        bash kaggle/retrain-weekly.sh
        ;;
    track)
        say "=== ELO TRACKING ==="
        LATEST_PANEL=$(ls -t kaggle-out/*/panel/results.json 2>/dev/null | head -1)
        if [ -n "$LATEST_PANEL" ]; then
            .venv/bin/python tools/track_elo.py "$LATEST_PANEL" --label "$WEEK"
        else
            say "No panel results found"
        fi
        ;;
    all)
        say "=== FULL WEEKLY LOOP: $WEEK ==="
        say "Step 1/3: GPU Training"
        bash kaggle/launch-train-g5-h1024.sh
        
        say "Step 2/3: CPU Self-Play Fleet"
        bash kaggle/selfplay-fleet.sh
        
        say "Step 3/3: Elo Tracking"
        LATEST_PANEL=$(ls -t kaggle-out/*/panel/results.json 2>/dev/null | head -1)
        if [ -n "$LATEST_PANEL" ]; then
            .venv/bin/python tools/track_elo.py "$LATEST_PANEL" --label "$WEEK"
        fi
        say "Weekly loop complete. Next: wait for panel, then retrain next Saturday."
        ;;
    *)
        echo "Usage: $0 [train|fleet|retrain|track|all]"
        exit 1
        ;;
esac