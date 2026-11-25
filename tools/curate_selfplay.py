#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy
"""
Curate self-play PGN for training data quality.

Filters:
- Decisive games only (1-0, 0-1) — draws are low information
- Minimum game length (avoid trivial openings)
- Positional entropy filter (high entropy = complex positions)
- Blunder detection (positions where eval swings > 300 cp)
- Deduplication by position hash (first 12 plies)
- Balanced result distribution (not all White wins)

Output: curated PGN ready for training pipeline.
"""

import argparse
import chess
import chess.pgn
import hashlib
import os
import sys
from collections import defaultdict

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]

def position_key(board: chess.Board) -> str:
    """Stable key for deduplication: first 12 plies only."""
    fen = board.fen()
    # Use only piece placement + side to move + castling + ep (no move counters)
    parts = fen.split(' ')[:4]
    return ' '.join(parts)

def evaluate_entropy(board: chess.Board) -> float:
    """Shannon entropy of legal move distribution (proxy for position complexity)."""
    moves = list(board.legal_moves)
    if not moves:
        return 0.0
    # Uniform prior -> log2(N)
    import math
    return math.log2(len(moves))

def has_blunder_swing(prev_score_cp: int, curr_score_cp: int, threshold_cp: int = 300) -> bool:
    """Detect if eval swung more than threshold (crude blunder proxy)."""
    return abs(curr_score_cp - prev_score_cp) > threshold_cp

def curate_pgn(input_path: str, output_path: str,
               min_moves: int = 20,
               min_entropy: float = 3.0,
               blunder_threshold_cp: int = 300,
               max_games: int = 0,
               balance_results: bool = True) -> dict:
    """
    Read input PGN, write curated games to output.
    Returns stats dict.
    """
    stats = {
        'total': 0,
        'decisive': 0,
        'min_moves': 0,
        'entropy_pass': 0,
        'blunder_pass': 0,
        'dedup_pass': 0,
        'written': 0,
        'skipped_draw': 0,
        'skipped_short': 0,
        'skipped_low_entropy': 0,
        'skipped_no_blunder': 0,
        'skipped_dup': 0,
        'skipped_balance': 0,
    }
    
    seen_positions = set()
    result_counts = {'1-0': 0, '0-1': 0}
    
    with open(input_path, 'r') as inf, open(output_path, 'w') as outf:
        while True:
            game = chess.pgn.read_game(inf)
            if game is None:
                break
            
            stats['total'] += 1
            
            # 1. Decisive only
            result = game.headers.get('Result', '*')
            if result not in ('1-0', '0-1'):
                stats['skipped_draw'] += 1
                continue
            stats['decisive'] += 1
            
            # 2. Minimum game length
            move_count = sum(1 for _ in game.mainline_moves())
            if move_count < min_moves:
                stats['skipped_short'] += 1
                continue
            stats['min_moves'] += 1
            
            # 3. Entropy filter (sample positions every 8 plies)
            board = game.board()
            entropy_sum = 0.0
            entropy_samples = 0
            for i, move in enumerate(game.mainline_moves()):
                if i % 8 == 0:
                    entropy_sum += evaluate_entropy(board)
                    entropy_samples += 1
                board.push(move)
            avg_entropy = entropy_sum / entropy_samples if entropy_samples else 0
            if avg_entropy < min_entropy:
                stats['skipped_low_entropy'] += 1
                continue
            stats['entropy_pass'] += 1
            
            # 4. Blunder detection (replay with simple material eval proxy)
            # Since we don't have engine scores, use material + mobility swing
            board = game.board()
            prev_material = 0
            has_blunder = False
            for move in game.mainline_moves():
                board.push(move)
                # Crude material count
                material = 0
                for piece_type in (chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN):
                    material += len(board.pieces(piece_type, chess.WHITE)) * [100, 320, 330, 500, 900][piece_type - 1]
                    material -= len(board.pieces(piece_type, chess.BLACK)) * [100, 320, 330, 500, 900][piece_type - 1]
                if abs(material - prev_material) > blunder_threshold_cp:
                    has_blunder = True
                    break
                prev_material = material
            if not has_blunder:
                stats['skipped_no_blunder'] += 1
                continue
            stats['blunder_pass'] += 1
            
            # 5. Deduplication by early position key
            board = game.board()
            dup = False
            for i, move in enumerate(game.mainline_moves()):
                if i >= 12:
                    break
                key = position_key(board)
                if key in seen_positions:
                    dup = True
                    break
                seen_positions.add(key)
                board.push(move)
            if dup:
                stats['skipped_dup'] += 1
                continue
            stats['dedup_pass'] += 1
            
            # 6. Balance results (roughly 50/50)
            if balance_results:
                total_written = result_counts['1-0'] + result_counts['0-1']
                if total_written > 10:
                    ratio = result_counts[result] / total_written
                    if ratio > 0.65:  # cap at 65%
                        stats['skipped_balance'] += 1
                        continue
            
            # Write game
            print(game, file=outf, end='\n\n')
            result_counts[result] += 1
            stats['written'] += 1
            
            if max_games and stats['written'] >= max_games:
                break
    
    return stats

def main():
    ap = argparse.ArgumentParser(description='Curate self-play PGN for training')
    ap.add_argument('input', help='Input PGN file')
    ap.add_argument('output', help='Output curated PGN file')
    ap.add_argument('--min-moves', type=int, default=20, help='Minimum game length (plies)')
    ap.add_argument('--min-entropy', type=float, default=3.0, help='Minimum average entropy (bits)')
    ap.add_argument('--blunder-threshold', type=int, default=300, help='Material swing threshold (cp)')
    ap.add_argument('--max-games', type=int, default=0, help='Max games to output (0 = unlimited)')
    ap.add_argument('--no-balance', action='store_true', help='Disable result balancing')
    args = ap.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Input not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    
    stats = curate_pgn(
        args.input, args.output,
        min_moves=args.min_moves,
        min_entropy=args.min_entropy,
        blunder_threshold_cp=args.blunder_threshold,
        max_games=args.max_games,
        balance_results=not args.no_balance
    )
    
    print("=== Curation Stats ===")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    if stats['total']:
        print(f"  Retention: {stats['written']}/{stats['total']} = {100*stats['written']/stats['total']:.1f}%")

if __name__ == '__main__':
    main()