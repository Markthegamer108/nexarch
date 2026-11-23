# Position databases

Every source of chess positions with evaluations that is publicly available, what it costs, and what we can do with it.
Updated 2026-11-23.

## In the training pool

| Source | Positions | Size | Labels | Licence | Status |
|---|---|---|---|---|---|
| Lichess fishnet-evals 2025-01 | 435,613,130 | 14 GB | Stockfish, per position | CC0 | on Kaggle |
| Lichess evaluation database | 289,759,105 | 9 GB | Stockfish, per position | CC0 | on Kaggle |
| Lc0 T80 2024 Jan/Feb/Mar | 1,200,695,328 | 37 GB | Leela visits | CC0 | on Kaggle |
| Gen 3 graded core | 33,516,621 | 1 GB | 33-engine panel + Lc0 | ours | on Kaggle |
| Gen 3/4 self-play | 83,101,759 | 2.7 GB | own search | ours | on Kaggle |
| AWS self-play 2026-11-23 | 1,189,526 | 38 MB | Gen 4 search | ours | on Kaggle |

## Being ingested now

| Source | Raw size | Usable estimate | Labels | Licence | Blocker |
|---|---|---|---|---|---|
| Lichess fishnet-evals, months 2013-01..2025-03 | 415 GB parquet | ~1B positions at `every=5`, ~4B at `every=1` | Stockfish | CC0 | disk throughput only |
| official-stockfish/master-binpacks | 287.1 GB binpack | ~4B | Stockfish, 5000+ nodes, farseer | ODbL | redistribution terms |

## Not yet usable

| Source | Size | Why not |
|---|---|---|
| Lc0 training data, test80 hourly tars | 12,686 tars, ~15 TB | raw tar of gz chunks, needs Leela's rescorer, not binpack |
| Lc0 test79 / test78 / test71 / test60 tars | thousands of tars | same |
| Chessmont open database | 1.35B FENs | positions only, no evaluations |
| Lichess standard games | ~6B positions | positions only, no evaluations |
| Lichess puzzles | ~5M | has solutions, no evaluation |
| Syzygy tablebases (6-piece) | ~150 GB | perfect endgame labels, but needs endgame selection |
| CCRL / CEGT / Caissabase PGNs | hundreds of GB | positions only, no evaluations |

## Community sets on Hugging Face, smaller and lower value

| Dataset | Size | Columns | Note |
|---|---|---|---|
| mateuszgrzyb/lichess-stockfish-normalized | 6.6 GB | fen, depth, cp, mate | CC-BY-4.0, overlaps fishnet |
| blue-prince/chess-1b-positions | 16.5 GB | fen, best_move, depth, eval_cp, mate_in | many null labels |
| ssingh22/chess-evaluations | 16.3 GB | MCTS + evals | Leela-style, small |
| ababoin07/chess_positions_depth_14 | ~100M rows | FEN, score text | single-column text, slow to parse |
| AGundawar/chess_position_evaluations | 10M-100M | CSV | apache-2.0, unverified depth |

## What matters

1. **Stockfish's own binpacks are the single best source we do not yet use.** Same format family our converter already reads, labels from 5000-node searches and farseer runs, not from a browser's 1-second analysis.
2. **fishnet at `every=1` is 5x bigger than what we are taking.** We are currently sampling 1 in 5 rows; the cost of taking all of them is 5x the download and 5x the Kaggle datasets.
3. **Raw Leela tars are 15 TB and need a different converter.** Worth writing only if the first two run dry.
4. **Unlabelled position sets are not training data.** They become training data only after someone searches them, at engine cost.
