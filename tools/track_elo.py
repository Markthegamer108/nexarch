#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
"""
Track Elo vs Stockfish 19 from panel results.
Parses panel results.json, computes Elo difference vs Stockfish 19,
maintains history, alerts when target (+300) is reached.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

HISTORY_FILE = Path("nets/elo_history.json")
TARGET_ELO_GAIN = 300  # vs Stockfish 19
STOCKFISH_NAME = "Stockfish 19"

def load_history():
    if HISTORY_FILE.exists():
        return json.loads(HISTORY_FILE.read_text())
    return []

def save_history(history):
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history, indent=2))

def parse_results(results_path):
    with open(results_path) as f:
        return json.load(f)

def extract_elo_vs_stockfish(data):
    """Return (candidate_elo, gen4_elo) vs Stockfish 19, or (None, None) if not found."""
    for opp in data.get("opponents", []):
        if opp["opponent"] == STOCKFISH_NAME:
            cand = opp["candidate"]
            gen4 = opp["gen4"]
            return cand["elo"], gen4["elo"]
    return None, None

def main():
    ap = argparse.ArgumentParser(description="Track Elo vs Stockfish 19 from panel results")
    ap.add_argument("results", help="panel/results.json from panel_match.py")
    ap.add_argument("--label", default="", help="Label for this run (e.g., week number)")
    ap.add_argument("--alert", action="store_true", help="Exit non-zero if target reached")
    args = ap.parse_args()
    
    if not os.path.exists(args.results):
        print(f"Results not found: {args.results}", file=sys.stderr)
        sys.exit(1)
    
    data = parse_results(args.results)
    cand_elo, gen4_elo = extract_elo_vs_stockfish(data)
    
    if cand_elo is None:
        print(f"{STOCKFISH_NAME} not found in panel results", file=sys.stderr)
        sys.exit(1)
    
    # Negative Elo means we're behind Stockfish
    # Target: candidate Elo >= -50 (i.e., within 50 of SF19) or gain of +300 over baseline
    baseline_elo = -470  # Gen 4 vs SF19 from first panel
    gain = cand_elo - baseline_elo
    
    label = args.label or datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    entry = {
        "date": datetime.utcnow().isoformat() + "Z",
        "label": label,
        "candidate_elo_vs_sf19": round(cand_elo, 1),
        "gen4_elo_vs_sf19": round(gen4_elo, 1),
        "gain_vs_baseline": round(gain, 1),
        "target_gain": TARGET_ELO_GAIN,
        "target_reached": gain >= TARGET_ELO_GAIN
    }
    
    history = load_history()
    history.append(entry)
    save_history(history)
    
    # Print current status
    print("=== Elo Tracking vs Stockfish 19 ===")
    print(f"Run:           {label}")
    print(f"Candidate:     {cand_elo:+.1f} Elo")
    print(f"Gen 4 baseline:{gen4_elo:+.1f} Elo")
    print(f"Gain vs base:  {gain:+.1f} Elo")
    print(f"Target:        +{TARGET_ELO_GAIN} Elo")
    print(f"Progress:      {gain/TARGET_ELO_GAIN*100:.1f}%")
    print()
    
    if gain >= TARGET_ELO_GAIN:
        print("🎯 TARGET REACHED: Candidate is +300 Elo over Gen 4 baseline!")
        print("   Gen 5 is ready for release validation.")
    else:
        remaining = TARGET_ELO_GAIN - gain
        print(f"📈 {remaining:.1f} Elo to go")
    
    print()
    print("History:")
    for h in history[-10:]:
        marker = " 🎯" if h["target_reached"] else ""
        print(f"  {h['date'][:10]}  {h['label']:20s}  cand: {h['candidate_elo_vs_sf19']:+6.1f}  gain: {h['gain_vs_baseline']:+6.1f}{marker}")
    
    if args.alert and gain >= TARGET_ELO_GAIN:
        sys.exit(0)  # Success - target reached
    elif args.alert:
        sys.exit(1)  # Not yet

if __name__ == "__main__":
    main()