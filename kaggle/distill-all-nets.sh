#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# DISTILL ALL ACQUIRED NETS: Use every downloaded NNUE net to generate
# maximum training data via self-play and knowledge distillation.
#
# Strategy:
# 1. For each acquired net, run self-play games (diverse opponents = diverse positions)
# 2. Use strong nets as "teachers" - record their evaluations for our training targets
# 3. Mix all generated positions into master training set
# 4. This gives us the "knowledge" of every top engine without copying weights

set -euo pipefail
cd "$(dirname "$0")/.."

NETS_DIR="data/acquired/nets"
OUT_DIR="data/acquired/distilled"
mkdir -p "$OUT_DIR"
LOG="kaggle-out/distill-$(date -u +%Y%m%d-%H%M%S).log"
mkdir -p kaggle-out

. kaggle/lib.sh

say "=== DISTILLING ALL ACQUIRED NETS INTO TRAINING DATA ==="

# Find all acquired nets
NETS=($(find "$NETS_DIR" -name "*.nnue" -type f | sort))
say "Found ${#NETS[@]} nets to distill"

if [ ${#NETS[@]} -eq 0 ]; then
    say "No nets found in $NETS_DIR"
    exit 1
fi

# We need a Stockfish-compatible engine binary to run these nets
# Most are Stockfish-format NNUE, so we can use our engine or Stockfish
ENGINE_BIN="engine/nexarch-cpu"
if [ ! -x "$ENGINE_BIN" ]; then
    say "Building engine..."
    bash kaggle/setup-engines.sh 2>&1 | tail -5
fi

# For each net, generate self-play games
# We'll run in parallel batches on Kaggle CPU
BATCH_SIZE=5
TOTAL_GAMES_PER_NET=200  # 200 games per net = ~20k positions per net

say "Launching distillation fleet on Kaggle..."

# Create a master script that each worker runs
cat > "$OUT_DIR/worker.py" <<'PY'
#!/usr/bin/env python3
import subprocess, chess, chess.engine, chess.pgn, random, time, os, sys
from pathlib import Path

net_path = sys.argv[1]
output_pgn = sys.argv[2]
games = int(sys.argv[3])
tc_ms = int(sys.argv[4])

engine_bin = "/tmp/nexarch/nexarch-cpu"
if not os.path.exists(engine_bin):
    # Copy from input dataset
    import shutil, glob
    for e in glob.glob("/kaggle/input/*/engine/nexarch-cpu"):
        shutil.copy2(e, engine_bin)
        os.chmod(engine_bin, 0o755)
        break

eng = chess.engine.SimpleEngine.popen_uci(engine_bin)
eng.configure({"Threads": 1, "Hash": 64, "EvalFile": net_path})

with open(output_pgn, "w") as f:
    for g in range(games):
        board = chess.Board()
        game = chess.pgn.Game()
        game.headers["Event"] = f"Distillation {os.path.basename(net_path)}"
        game.headers["Site"] = "Kaggle CPU"
        game.headers["Date"] = time.strftime("%Y.%m.%d", time.gmtime())
        game.headers["Round"] = str(g+1)
        game.headers["White"] = f"Nexarch-{os.path.basename(net_path)}"
        game.headers["Black"] = f"Nexarch-{os.path.basename(net_path)}"
        game.headers["TimeControl"] = f"{tc_ms/1000}+0"
        node = game
        
        while not board.is_game_over(claim_draw=True):
            result = eng.play(board, chess.engine.Limit(time=tc_ms/1000.0))
            board.push(result.move)
            node = node.add_variation(result.move)
        
        game.headers["Result"] = board.result(claim_draw=True)
        print(game, file=f, end="\n\n")
        
        if (g+1) % 50 == 0:
            print(f"  {os.path.basename(net_path)}: {g+1}/{games}", flush=True)

eng.quit()
print(f"DONE {net_path} -> {output_pgn}")
PY

# Launch on Kaggle for each net (in batches)
for i in "${!NETS[@]}"; do
    net="${NETS[i]}"
    net_name=$(basename "$net" .nnue)
    
    # Skip if already done
    if [ -f "$OUT_DIR/${net_name}.pgn.zst" ]; then
        say "  Skip $net_name (already distilled)"
        continue
    fi
    
    say "  Launching distillation for $net_name (${i}+1/${#NETS[@]})"
    
    push_kernel "distill-${net_name}" 4 .venv/bin/python kaggle/job.py --name "distill-${net_name}" --internet \
        --dataset markthegamer108/nexarch-engines \
        --cmd "cd /kaggle/working && \
               mkdir -p /tmp/nexarch && \
               cp /kaggle/input/nexarch-engines/engine/nexarch-cpu /tmp/nexarch/ && \
               chmod +x /tmp/nexarch/nexarch-cpu && \
               NET_PATH=\$(find /kaggle/input -name '$(basename "$net")' -print -quit) && \
               if [ -z \"\$NET_PATH\" ]; then echo 'Net not found in inputs'; exit 1; fi && \
               python3 -c '
import subprocess, chess, chess.engine, chess.pgn, random, time, os, sys
net_path = sys.argv[1]
output_pgn = sys.argv[2]
games = int(sys.argv[3])
tc_ms = int(sys.argv[4])
engine_bin = \"/tmp/nexarch/nexarch-cpu\"
eng = chess.engine.SimpleEngine.popen_uci(engine_bin)
eng.configure({\"Threads\": 1, \"Hash\": 64, \"EvalFile\": net_path})
with open(output_pgn, \"w\") as f:
    for g in range(games):
        board = chess.Board()
        game = chess.pgn.Game()
        game.headers[\"Event\"] = f\"Distillation {os.path.basename(net_path)}\"
        game.headers[\"Site\"] = \"Kaggle CPU\"
        game.headers[\"Date\"] = time.strftime(\"%Y.%m.%d\", time.gmtime())
        game.headers[\"Round\"] = str(g+1)
        game.headers[\"White\"] = f\"Nexarch-{os.path.basename(net_path)}\"
        game.headers[\"Black\"] = f\"Nexarch-{os.path.basename(net_path)}\"
        game.headers[\"TimeControl\"] = f\"{tc_ms/1000}+0\"
        node = game
        while not board.is_game_over(claim_draw=True):
            result = eng.play(board, chess.engine.Limit(time=tc_ms/1000.0))
            board.push(result.move)
            node = node.add_variation(result.move)
        game.headers[\"Result\"] = board.result(claim_draw=True)
        print(game, file=f, end=\"\n\n\")
        if (g+1) % 50 == 0:
            print(f\"  {os.path.basename(net_path)}: {g+1}/{games}\", flush=True)
eng.quit()
' \"\$NET_PATH\" \"/tmp/${net_name}.pgn\" ${TOTAL_GAMES_PER_NET} 500 && \
               zstd -q -19 \"/tmp/${net_name}.pgn\" -o \"/tmp/${net_name}.pgn.zst\" && \
               ls -lh /tmp/${net_name}.pgn.zst" \
        --push &
    
    # Throttle launches
    if [ $(( (i+1) % BATCH_SIZE )) -eq 0 ]; then
        say "  Waiting for batch to launch..."
        sleep 10
    fi
done

say "All distillation jobs launched. Waiting for completion..."
wait

say "Downloading distilled PGNs..."
for net in "${NETS[@]}"; do
    net_name=$(basename "$net" .nnue)
    .venv/bin/kaggle kernels output "distill-${net_name}" -p "$OUT_DIR/$net_name" 2>&1 | grep -E "Downloading|pgn" || true
    if [ -f "$OUT_DIR/$net_name/${net_name}.pgn.zst" ]; then
        mv "$OUT_DIR/$net_name/${net_name}.pgn.zst" "$OUT_DIR/"
        say "  Got $net_name"
    fi
done

# Combine all distilled games
say "Combining all distilled games..."
COMBINED="$OUT_DIR/all-distilled-$(date -u +%Y%m%d).pgn"
cat "$OUT_DIR"/*.pgn.zst 2>/dev/null | zstd -d > "$COMBINED" || true
GAME_COUNT=$(grep -c '^\[Event ' "$COMBINED" 2>/dev/null || echo 0)
say "Combined $GAME_COUNT games -> $COMBINED"

# Curate
say "Curating distilled games..."
.venv/bin/python tools/curate_selfplay.py "$COMBINED" "$OUT_DIR/all-distilled-curated.pgn" \
    --min-moves 20 --min-entropy 3.0 --blunder-threshold 300 --max-games 500000

# Upload curated dataset
UPLOAD_DIR=$(mktemp -d)
cp "$OUT_DIR/all-distilled-curated.pgn" "$UPLOAD_DIR/distilled-$(date -u +%Y%m%d).pgn"
cat > "$UPLOAD_DIR/dataset-metadata.json" <<EOF
{"title":"nexarch-distilled-$(date -u +%Y%m%d)","id":"markthegamer108/nexarch-distilled-$(date -u +%Y%m%d)","licenses":[{"name":"MIT"}]}
EOF
echo "MIT License..." > "$UPLOAD_DIR/LICENSE"
.venv/bin/kaggle datasets create -p "$UPLOAD_DIR" --public 2>&1 | tail -3
say "Uploaded: markthegamer108/nexarch-distilled-$(date -u +%Y%m%d)"

say "=== DISTILLATION COMPLETE ==="
say "Curated distilled games: $OUT_DIR/all-distilled-curated.pgn"
say "Add to training: data/acquired/distilled/all-distilled-curated.pgn"