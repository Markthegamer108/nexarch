#pragma once

#include <atomic>
#include <chrono>
#include <vector>

#include "nnue.h"
#include "tt.h"

struct Limits {
  int depth = MAX_PLY - 1;
  u64 nodes = 0;
  u64 soft_nodes = 0;
  i64 soft_ms = 0;
  i64 hard_ms = 0;
  bool uci_limit_strength = false;
  int uci_elo = 1500;
  int skill_level = 20;
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
  void clear();
  void set_network(const nnue::Network* net) { net_ = net; }
  int static_eval(const Position& pos);
  u64 node_count() const { return nodes_.load(std::memory_order_relaxed); }

  std::vector<u64> game_keys;
  bool print_info = true;
  int thread_id = 0;
  std::vector<const Searcher*> peers;

 private:
  struct Frame {
    Move move = NO_MOVE;
    int piece = NO_PIECE;
    int static_eval = NO_SCORE;
    Move excluded = NO_MOVE;
    Move killers[2] = {NO_MOVE, NO_MOVE};
  };

  int search(const Position& pos, int alpha, int beta, int depth, int ply, bool cutnode);
  int qsearch(const Position& pos, int alpha, int beta, int ply);
  int evaluate(const Position& pos, int ply);
  int evaluate_with_noise(const Position& pos, int ply);
  int max_depth_limit() const;
  Move pick_move_for_skill(const MoveList& list, const int* scores, Move best_move) const;
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
  std::vector<int> continuation_;
  int capture_history_[12][64][6];
  int correction_[2][CORRECTION_SIZE];
  Frame stack_[MAX_PLY + 8];
  u64 keys_[MAX_PLY + 8];
  Move pv_[MAX_PLY + 1][MAX_PLY + 1];
  int pv_len_[MAX_PLY + 1];
  std::vector<nnue::Accumulator> acc_;
};
