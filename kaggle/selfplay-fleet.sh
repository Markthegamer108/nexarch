#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Launches a fleet of Kaggle CPU workers for distributed self-play.
# Each worker pulls the latest net, plays games, uploads curated PGN.
# Run after a new net is published (e.g., Saturday after GPU training).

set -euo pipefail
cd "$(dirname "$0")/.."

WORKERS=${SELFPLAY_WORKERS:-20}
GAMES_PER_WORKER=${SELFPLAY_GAMES:-500}
TC_MIX=${SELFPLAY_TC:-"100 1000 10000"}   # ms per move: fast/medium/slow
THREADS=${SELFPLAY_THREADS:-1}
HASH=${SELFPLAY_HASH:-64}
NAME_PREFIX=${SELFPLAY_PREFIX:-nexarch-selfplay-fleet}
NET_DATASET=${SELFPLAY_NET_DS:-markthegamer108/nexarch-latest-net}
OUT_DIR=kaggle-out/selfplay-fleet-$(date -u +%Y%m%d-%H%M%S)
mkdir -p "$OUT_DIR"
LOG="$OUT_DIR/fleet.log"

. kaggle/lib.sh

say "Self-play fleet: $WORKERS workers, $GAMES_PER_WORKER games each, TC=$TC_MIX"

# Find latest net from the net dataset
say "Fetching latest net from $NET_DATASET..."
NET_PATH=$(mktemp -u --suffix=.nnue)
.venv/bin/kaggle datasets download -d "$NET_DATASET" -f nexarch.nnue -p /tmp 2>&1 | tail -5
if [ ! -f /tmp/nexarch.nnue ]; then
    say "ERROR: Could not download net from $NET_DATASET"
    exit 1
fi
cp /tmp/nexarch.nnue "$NET_PATH"
say "Net ready at $NET_PATH"

# Upload net to a temporary dataset for workers to pull
NET_DS="markthegamer108/nexarch-selfplay-net-$(date -u +%Y%m%d-%H%M%S)"
NET_DIR=$(mktemp -d)
cp "$NET_PATH" "$NET_DIR/nexarch.nnue"
cat > "$NET_DIR/dataset-metadata.json" <<EOF
{"title":"nexarch-selfplay-net-$(date -u +%Y%m%d-%H%M%S)","id":"markthegamer108/nexarch-selfplay-net-$(date -u +%Y%m%d-%H%M%S)","licenses":[{"name":"MIT"}]}
EOF
echo "MIT License

Copyright (c) 2026 Mark Ivanovskyy

Permission is hereby granted..." > "$NET_DIR/LICENSE"
.venv/bin/kaggle datasets create -p "$NET_DIR" --public 2>&1 | tail -3
say "Net uploaded to $NET_DS"

# Launch workers
PIDS=()
for w in $(seq 1 "$WORKERS"); do
    WNAME="${NAME_PREFIX}-w${w}"
    say "Launching worker $w/$WORKERS: $WNAME"
    
    push_kernel "$WNAME" 4 .venv/bin/python kaggle/job.py --name "$WNAME" --internet \
        --dataset "$NET_DS" \
        --dataset markthegamer108/nexarch-engines \
        --cmd "cd /kaggle/working && \
               mkdir -p /tmp/nexarch && \
               cp /kaggle/input/nexarch-selfplay-net-*/nexarch.nnue /tmp/nexarch/ && \
               cp /kaggle/input/nexarch-engines/engine/nexarch-cpu /tmp/nexarch/ && \
               chmod +x /tmp/nexarch/nexarch-cpu && \
               python -c '
import subprocess, random, os, sys, time, chess, chess.pgn, chess.engine
tc_ms = [100, 1000, 10000]
games = 0
pgn_path = \"/tmp/selfplay-\$(date -u +%Y%m%d-%H%M%S)-w${w}.pgn\"
with open(pgn_path, \"w\") as pgn_f:
    while games < ${GAMES_PER_WORKER}:
        tc = random.choice(tc_ms)
        eng = chess.engine.SimpleEngine.popen_uci(\"/tmp/nexarch/nexarch-cpu\")
        eng.configure({\"Threads\": ${THREADS}, \"Hash\": ${HASH}, \"EvalFile\": \"/tmp/nexarch/nexarch.nnue\"})
        board = chess.Board()
        game = chess.pgn.Game()
        game.headers[\"Event\"] = \"Nexarch Self-Play\"
        game.headers[\"Site\"] = \"Kaggle CPU Fleet\"
        game.headers[\"Date\"] = time.strftime(\"%Y.%m.%d\", time.gmtime())
        game.headers[\"Round\"] = str(games + 1)
        game.headers[\"White\"] = \"Nexarch Self-Play\"
        game.headers[\"Black\"] = \"Nexarch Self-Play\"
        game.headers[\"TimeControl\"] = f\"{tc/1000}+0\"
        node = game
        move_count = 0
        while not board.is_game_over(claim_draw=True):
            result = eng.play(board, chess.engine.Limit(time=tc/1000.0))
            board.push(result.move)
            node = node.add_variation(result.move)
            move_count += 1
            if move_count > 256:
                break
        eng.quit()
        game.headers[\"Result\"] = board.result(claim_draw=True)
        print(game, file=pgn_f, end=\"\\n\\n\")
        games += 1
        if games % 50 == 0:
            print(f\"Worker w${w}: {games}/{${GAMES_PER_WORKER}} games\", flush=True)
' && \
               python tools/curate_selfplay.py \$(ls /tmp/selfplay-*.pgn | head -1) /tmp/curated-\$(date -u +%Y%m%d-%H%M%S)-w${w}.pgn && \
               ls -lh /tmp/curated-*.pgn" \
        --push &
    PIDS+=($!)
    sleep 2  # stagger launches
done

say "All $WORKERS workers launched. Waiting for completion..."
for pid in "${PIDS[@]}"; do
    wait "$pid" || say "Worker PID $pid failed"
done

say "Fleet complete. Downloading curated games..."
# Download all curated PGNs from worker outputs
for w in $(seq 1 "$WORKERS"); do
    WNAME="${NAME_PREFIX}-w${w}"
    .venv/bin/kaggle kernels output "$WNAME" -p "$OUT_DIR/worker-$w" 2>&1 | grep -E "curated.*\.pgn|Downloading" || true
done

# Combine all curated games
COMBINED="$OUT_DIR/combined-$(date -u +%Y%m%d).pgn"
cat "$OUT_DIR"/worker-*/curated-*.pgn 2>/dev/null > "$COMBINED" || true
if [ -s "$COMBINED" ]; then
    GAME_COUNT=$(grep -c '^\[Event ' "$COMBINED")
    say "Combined $GAME_COUNT curated games -> $COMBINED"
    
    # Upload combined dataset
    UPLOAD_DIR=$(mktemp -d)
    cp "$COMBINED" "$UPLOAD_DIR/selfplay-$(date -u +%Y%m%d).pgn"
    cat > "$UPLOAD_DIR/dataset-metadata.json" <<EOF
{"title":"nexarch-selfplay-$(date -u +%Y%m%d)","id":"markthegamer108/nexarch-selfplay-$(date -u +%Y%m%d)","licenses":[{"name":"MIT"}]}
EOF
    echo "MIT License..." > "$UPLOAD_DIR/LICENSE"
    .venv/bin/kaggle datasets create -p "$UPLOAD_DIR" --public 2>&1 | tail -3
    say "Self-play dataset uploaded: markthegamer108/nexarch-selfplay-$(date -u +%Y%m%d)"
else
    say "WARNING: No curated games collected"
fi

say "Fleet log: $LOG"