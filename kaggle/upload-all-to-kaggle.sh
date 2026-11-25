#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
#
# Upload all local acquired data to Kaggle datasets, then clean local.
# Run after acquire-all-data.sh finishes downloading.

set -euo pipefail
cd "$(dirname "$0")/.."

ACQUIRED="data/acquired"
UPLOADED_LOG="$ACQUIRED/master/uploaded_datasets.txt"
mkdir -p "$ACQUIRED/master"
touch "$UPLOADED_LOG"

. kaggle/lib.sh

say "=== UPLOAD ALL ACQUIRED DATA TO KAGGLE ==="

upload_file() {
    local file="$1" category="$2"
    local base=$(basename "$file")
    local slug="nexarch-${category}-${base%.*}"
    slug=$(echo "$slug" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | cut -c1-60)
    
    # Check if already uploaded
    if grep -q "^$slug$" "$UPLOADED_LOG" 2>/dev/null; then
        say "  Skip $slug (already uploaded)"
        return 0
    fi
    
    say "  Uploading $file -> markthegamer108/$slug"
    local ds_dir=$(mktemp -d)
    cp "$file" "$ds_dir/$base"
    cat > "$ds_dir/dataset-metadata.json" <<META
{"title":"$slug","id":"markthegamer108/$slug","licenses":[{"name":"MIT"}]}
META
    echo "MIT License..." > "$ds_dir/LICENSE"
    
    if .venv/bin/kaggle datasets create -p "$ds_dir" --public 2>&1 | tail-3; then
        say "    ✓ Uploaded ($(du -h "$file" | cut -f1)), deleting local"
        rm -f "$file"
        echo "$slug" >> "$UPLOADED_LOG"
        return 0
    else
        say "    ✗ FAILED, keeping local"
        return 1
    fi
}

# Upload all files in acquired subdirs
for cat in fishtest lc0 nets games seer ethereal distilled; do
    dir="$ACQUIRED/$cat"
    [ -d "$dir" ] || continue
    say "--- Category: $cat ---"
    for f in "$dir"/*; do
        [ -f "$f" ] || continue
        # Skip small scripts
        [[ "$f" == *.py ]] && continue
        [[ "$f" == *.sh ]] && continue
        upload_file "$f" "$cat" || true
    done
done

say "=== UPLOAD COMPLETE ==="
say "Log: $UPLOADED_LOG"
say "Local space freed:"
du -sh "$ACQUIRED" 2>/dev/null
