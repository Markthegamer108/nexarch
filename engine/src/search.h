// Alpha-beta search: iterative deepening, PVS, transposition table, quiescence, null-move/futility/LMR pruning,
// singular extensions and learned move-ordering tables (butterfly, continuation, capture and correction history).
#pragma once

#include <atomic>
#include <chrono>
#include <vector>

#include "nnue.h"
#include "tt.h"

struct Limits {
  int depth = MAX_PLY - 1;
  u64 nodes = 0;       // hard node limit (0 = none)
  u64 soft_nodes = 0;  // finish the current iteration, then stop once this many nodes are searched
  i64 soft_ms = 0;     // don't start a new iteration after this much time (scaled by best-move stability)
  i64 hard_ms = 0;     // abort the search at this time
};

struct SearchResult {
  Move best = NO_MOVE;
  int score = 0;
  int depth = 0;
  u64 nodes = 0;
};

class Searcher {
 public:
  Searcher(TT& tt, std::atomic<bool>& stop);
  SearchResult go(const Position& root, const Limits& limits);
  void clear();  // forget everything learned about move ordering, e.g. for a new game
  void set_network(const nnue::Network* net) { net_ = net; }
  int static_eval(const Position& pos);
  u64 node_count() const { return nodes_.load(std::memory_order_relaxed); }

  std::vector<u64> game_keys;  // hash keys of the positions played before the root, oldest first
  bool print_info = true;
  int thread_id = 0;                   // Lazy SMP: 0 is the main thread, others are helpers
  std::vector<const Searcher*> peers;  // helper threads, so the main thread can report total nodes

 private:
  struct Frame {
    Move move = NO_MOVE;
    int piece = NO_PIECE;     // piece that made `move` (continuation history); NO_PIECE for null moves
    int static_eval = NO_SCORE;
    Move excluded = NO_MOVE;  // singular-extension verification search skips this move
    Move killers[2] = {NO_MOVE, NO_MOVE};
  };

  int search(const Position& pos, int alpha, int beta, int depth, int ply, bool cutnode);
  int qsearch(const Position& pos, int alpha, int beta, int ply);
  int evaluate(const Position& pos, int ply);
  int corrected(const Position& pos, int raw) const;
  void update_correction(const Position& pos, int depth, int diff);
  int quiet_history(const Position& pos, Move m, int ply) const;
  void update_quiet(const Position& pos, Move m, int ply, int bonus);
  int& capture_history(const Position& pos, Move m);
  int capture_history(const Position& pos, Move m) const;
  void score_moves(const Position& pos, const MoveList& list, int* scores, Move tt_move, int ply) const;
  bool repeated(const Position& pos, int ply) const;
  bool should_stop();
  i64 elapsed_ms() const;
  void report(int depth, int score) const;
  Frame& frame(int ply) { return stack_[ply + 2]; }
  const Frame& frame(int ply) const { return stack_[ply + 2]; }
  // Only this thread writes the counter; others read it, so a relaxed load/store pair is enough (no lock).
  void count_node() { nodes_.store(nodes_.load(std::memory_order_relaxed) + 1, std::memory_order_relaxed); }

  static constexpr int CORRECTION_SIZE = 16384;
  static constexpr int CORRECTION_GRAIN = 256;

  TT& tt_;
  std::atomic<bool>& stop_;
  std::atomic<u64> nodes_{0};
  const nnue::Network* net_ = nullptr;
  Limits limits_;
  std::chrono::steady_clock::time_point start_;
  bool stopped_ = false;
  int seldepth_ = 0;
  int root_depth_ = 0;
  int history_[2][64][64];
  std::vector<int> continuation_;  // [previous piece][previous to][piece][to]
  int capture_history_[12][64][6];
  int correction_[2][CORRECTION_SIZE];
  Frame stack_[MAX_PLY + 8];
  u64 keys_[MAX_PLY + 8];
  Move pv_[MAX_PLY + 1][MAX_PLY + 1];
  int pv_len_[MAX_PLY + 1];
  std::vector<nnue::Accumulator> acc_;
};
