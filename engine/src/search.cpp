#include "search.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <string>

namespace {

int LMR[64][64];

struct LmrTable {
  LmrTable() {
    for (int d = 1; d < 64; d++)
      for (int m = 1; m < 64; m++) LMR[d][m] = int(0.75 + std::log(double(d)) * std::log(double(m)) / 2.25);
  }
} lmr_table;

constexpr int PIECE_VALUE[6] = {100, 300, 300, 500, 900, 0};

int to_tt(int score, int ply) { return score >= MATE_BOUND ? score + ply : score <= -MATE_BOUND ? score - ply : score; }

int from_tt(int score, int ply) {
  if (score == NO_SCORE) return NO_SCORE;
  return score >= MATE_BOUND ? score - ply : score <= -MATE_BOUND ? score + ply : score;
}

bool bound_allows(int bound, int score, int alpha, int beta) {
  return bound == BOUND_EXACT || (bound == BOUND_LOWER && score >= beta) || (bound == BOUND_UPPER && score <= alpha);
}

// Generation-zero evaluation: nothing but piece counts. Everything else has to be learned.
int material_eval(const Position& pos) {
  int score = 0;
  for (int t = PAWN; t < KING; t++)
    score += PIECE_VALUE[t] * (popcount(pos.pcs[WHITE][t]) - popcount(pos.pcs[BLACK][t]));
  return pos.stm == WHITE ? score : -score;
}

void pick_next(MoveList& list, int* scores, int i) {
  int best = i;
  for (int j = i + 1; j < list.size; j++)
    if (scores[j] > scores[best]) best = j;
  std::swap(list.moves[i], list.moves[best]);
  std::swap(scores[i], scores[best]);
}

int captured_value(const Position& pos, Move m) {
  if (move_flag(m) == MF_EP) return PIECE_VALUE[PAWN];
  const int victim = pos.board[move_to(m)];
  return victim == NO_PIECE ? 0 : PIECE_VALUE[type_of(victim)];
}

// History tables saturate smoothly at +-16384 instead of overflowing.
void gravity(int& entry, int bonus) { entry += bonus - entry * std::abs(bonus) / 16384; }

int history_bonus(int depth) { return std::min(16 * depth * depth + 32 * depth, 1800); }

}  // namespace

Searcher::Searcher(TT& tt, std::atomic<bool>& stop)
    : tt_(tt), stop_(stop), continuation_(12 * 64 * 12 * 64), acc_(MAX_PLY + 8) {
  clear();
}

void Searcher::clear() {
  std::fill(&history_[0][0][0], &history_[0][0][0] + 2 * 64 * 64, 0);
  std::fill(continuation_.begin(), continuation_.end(), 0);
  std::fill(&capture_history_[0][0][0], &capture_history_[0][0][0] + 12 * 64 * 6, 0);
  std::fill(&correction_[0][0], &correction_[0][0] + 2 * CORRECTION_SIZE, 0);
}

i64 Searcher::elapsed_ms() const {
  return std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_).count();
}

int Searcher::evaluate(const Position& pos, int ply) {
  int v = net_ ? nnue::evaluate(*net_, acc_[ply], pos.stm) : material_eval(pos);
  v = v * (200 - pos.halfmove) / 200;  // drift toward a draw as the 50-move rule approaches
  return std::clamp(v, -MATE_BOUND + 1, MATE_BOUND - 1);
}

int Searcher::static_eval(const Position& pos) {
  if (net_) nnue::refresh(*net_, acc_[0], pos);
  return evaluate(pos, 0);
}

// Correction history: how far search results typically land from the static eval for this pawn structure.
int Searcher::corrected(const Position& pos, int raw) const {
  const int correction = correction_[pos.stm][pos.pawn_key % CORRECTION_SIZE] / CORRECTION_GRAIN;
  return std::clamp(raw + correction, -MATE_BOUND + 1, MATE_BOUND - 1);
}

void Searcher::update_correction(const Position& pos, int depth, int diff) {
  int& entry = correction_[pos.stm][pos.pawn_key % CORRECTION_SIZE];
  const int weight = std::min(depth + 1, 16);
  entry = std::clamp((entry * (256 - weight) + diff * CORRECTION_GRAIN * weight) / 256, -CORRECTION_GRAIN * 64,
                     CORRECTION_GRAIN * 64);
}

int Searcher::quiet_history(const Position& pos, Move m, int ply) const {
  const int piece = pos.board[move_from(m)], to = move_to(m);
  int score = history_[pos.stm][move_from(m)][to];
  for (int back = 1; back <= 2; back++) {
    const Frame& f = frame(ply - back);
    if (f.piece != NO_PIECE) score += continuation_[((f.piece * 64 + move_to(f.move)) * 12 + piece) * 64 + to];
  }
  return score;
}

void Searcher::update_quiet(const Position& pos, Move m, int ply, int bonus) {
  const int piece = pos.board[move_from(m)], to = move_to(m);
  gravity(history_[pos.stm][move_from(m)][to], bonus);
  for (int back = 1; back <= 2; back++) {
    const Frame& f = frame(ply - back);
    if (f.piece != NO_PIECE) gravity(continuation_[((f.piece * 64 + move_to(f.move)) * 12 + piece) * 64 + to], bonus);
  }
}

int& Searcher::capture_history(const Position& pos, Move m) {
  const int victim = move_flag(m) == MF_EP ? PAWN : pos.board[move_to(m)] == NO_PIECE ? KING : type_of(pos.board[move_to(m)]);
  return capture_history_[pos.board[move_from(m)]][move_to(m)][victim];
}

int Searcher::capture_history(const Position& pos, Move m) const {
  return const_cast<Searcher*>(this)->capture_history(pos, m);
}

bool Searcher::should_stop() {
  if (stopped_) return true;
  const u64 n = node_count();
  if (limits_.nodes && n >= limits_.nodes) return stopped_ = true;
  if ((n & 1023) == 0) {
    if (stop_.load(std::memory_order_relaxed)) return stopped_ = true;
    if (limits_.hard_ms && elapsed_ms() >= limits_.hard_ms) return stopped_ = true;
  }
  return false;
}

bool Searcher::repeated(const Position& pos, int ply) const {
  for (int d = 2; d <= pos.halfmove; d += 2) {
    const int idx = ply - d;
    u64 k;
    if (idx >= 0) {
      k = keys_[idx];
    } else {
      const int gi = int(game_keys.size()) + idx;
      if (gi < 0) break;
      k = game_keys[gi];
    }
    if (k == pos.key) return true;
  }
  return false;
}

void Searcher::score_moves(const Position& pos, const MoveList& list, int* scores, Move tt_move, int ply) const {
  const Frame& f = frame(ply);
  for (int i = 0; i < list.size; i++) {
    const Move m = list.moves[i];
    int s;
    if (m == tt_move) {
      s = 1 << 30;
    } else if (pos.is_noisy(m)) {
      s = captured_value(pos, m) * 16 + capture_history(pos, m);
      if (move_flag(m) == MF_PROMO) s += 16000;
      s += pos.see_ge(m, 0) ? (1 << 24) : -(1 << 24);
    } else if (m == f.killers[0]) {
      s = 1 << 23;
    } else if (m == f.killers[1]) {
      s = (1 << 23) - 1;
    } else {
      s = quiet_history(pos, m, ply);
    }
    scores[i] = s;
  }
}

SearchResult Searcher::go(const Position& root, const Limits& limits) {
  limits_ = limits;
  start_ = std::chrono::steady_clock::now();
  stopped_ = false;
  nodes_.store(0, std::memory_order_relaxed);
  if (thread_id == 0) tt_.new_search();
  for (Frame& f : stack_) f = Frame{};
  if (net_) nnue::refresh(*net_, acc_[0], root);
  keys_[0] = root.key;

  SearchResult result;
  {
    MoveList list;
    root.gen_moves(list, false);
    Position next;
    for (int i = 0; i < list.size && result.best == NO_MOVE; i++)
      if (root.make(list.moves[i], next)) result.best = list.moves[i];
  }
  if (result.best == NO_MOVE) {
    result.score = root.in_check() ? -MATE : 0;
    return result;
  }

  int previous = 0, stability = 0;
  Move last_best = NO_MOVE;
  // Helper threads start at staggered depths so they explore slightly different trees.
  for (int depth = 1 + (thread_id & 1); depth <= limits_.depth; depth++) {
    root_depth_ = depth;
    seldepth_ = 0;
    int delta = 18, alpha = -INF, beta = INF, score = 0;
    if (depth >= 5) {
      alpha = std::max(-INF, previous - delta);
      beta = std::min(INF, previous + delta);
    }
    while (true) {
      score = search(root, alpha, beta, depth, 0, false);
      if (stopped_) break;
      if (score <= alpha) {
        beta = (alpha + beta) / 2;
        alpha = std::max(-INF, score - delta);
      } else if (score >= beta) {
        beta = std::min(INF, score + delta);
      } else {
        break;
      }
      delta += delta / 2;
    }
    if (stopped_) break;
    if (pv_len_[0] > 0) result.best = pv_[0][0];
    result.score = previous = score;
    result.depth = depth;
    if (print_info) report(depth, score);

    // Time: stop early when the best move has been stable for a while, think longer when it keeps changing.
    stability = result.best == last_best ? std::min(stability + 1, 10) : 0;
    last_best = result.best;
    if (limits_.soft_ms) {
      const double scale = stability >= 6 ? 0.5 : stability >= 3 ? 0.8 : stability == 0 && depth > 6 ? 1.5 : 1.0;
      if (elapsed_ms() >= i64(double(limits_.soft_ms) * scale)) break;
    }
    if (limits_.soft_nodes && node_count() >= limits_.soft_nodes) break;
  }
  result.nodes = node_count();
  return result;
}

int Searcher::search(const Position& pos, int alpha, int beta, int depth, int ply, bool cutnode) {
  const bool pv_node = beta - alpha > 1;
  const bool root = ply == 0;
  const Move excluded = frame(ply).excluded;
  const bool in_check = pos.in_check();
  if (in_check) depth++;
  if (depth <= 0) return qsearch(pos, alpha, beta, ply);

  pv_len_[ply] = ply;
  count_node();
  if (should_stop()) return 0;
  seldepth_ = std::max(seldepth_, ply);
  if (!root) {
    if (pos.halfmove >= 100 || pos.insufficient_material() || repeated(pos, ply)) return 0;
    if (ply >= MAX_PLY - 1) return in_check ? 0 : evaluate(pos, ply);
    alpha = std::max(alpha, -MATE + ply);
    beta = std::min(beta, MATE - ply - 1);
    if (alpha >= beta) return alpha;
  }

  TTData tte{};
  const bool tt_hit = !excluded && tt_.probe(pos.key, tte);
  const Move tt_move = tt_hit ? tte.move : NO_MOVE;
  const int tt_score = tt_hit ? from_tt(tte.score, ply) : NO_SCORE;
  if (!pv_node && tt_hit && tte.depth >= depth && tt_score != NO_SCORE && bound_allows(tte.bound, tt_score, alpha, beta))
    return tt_score;

  int raw_eval = NO_SCORE, static_eval = NO_SCORE, eval = NO_SCORE;
  if (excluded) {
    static_eval = eval = frame(ply).static_eval;  // same position as the enclosing search
  } else if (!in_check) {
    raw_eval = tt_hit && tte.eval != NO_SCORE ? tte.eval : evaluate(pos, ply);
    static_eval = eval = corrected(pos, raw_eval);
    if (tt_score != NO_SCORE && bound_allows(tte.bound, tt_score, eval, eval)) eval = tt_score;
  }
  frame(ply).static_eval = static_eval;
  frame(ply + 2).killers[0] = frame(ply + 2).killers[1] = NO_MOVE;
  const bool improving = !in_check && frame(ply - 2).static_eval != NO_SCORE && static_eval > frame(ply - 2).static_eval;

  if (!pv_node && !in_check && !excluded) {
    // Reverse futility: far above beta at low depth, assume it holds.
    if (depth <= 8 && eval - 80 * (depth - improving) >= beta && eval < MATE_BOUND) return eval;

    // Null move: if passing still beats beta, the position is good enough to cut.
    if (depth >= 3 && eval >= beta && static_eval >= beta && frame(ply - 1).move != NULL_MOVE &&
        pos.has_non_pawn(pos.stm) && beta > -MATE_BOUND) {
      const int r = 3 + depth / 3 + std::min((eval - beta) / 200, 3);
      Position next;
      pos.make_null(next);
      frame(ply).move = NULL_MOVE;
      frame(ply).piece = NO_PIECE;
      keys_[ply + 1] = next.key;
      if (net_) nnue::copy(*net_, acc_[ply + 1], acc_[ply]);
      const int score = -search(next, -beta, -beta + 1, depth - r, ply + 1, !cutnode);
      if (stopped_) return 0;
      if (score >= beta) return score >= MATE_BOUND ? beta : score;
    }
  }

  // Internal iterative reduction: without a hash move this node is probably not that important.
  if (depth >= 4 && tt_move == NO_MOVE && (pv_node || cutnode) && !excluded) depth--;

  MoveList list;
  pos.gen_moves(list, false);
  int scores[MAX_MOVES];
  score_moves(pos, list, scores, tt_move, ply);

  Move quiets[64], captures[32];
  int n_quiets = 0, n_captures = 0, moves_tried = 0, best_score = -INF;
  Move best_move = NO_MOVE;
  bool skip_quiets = false;

  for (int i = 0; i < list.size; i++) {
    pick_next(list, scores, i);
    const Move m = list.moves[i];
    if (m == excluded) continue;
    const bool quiet = !pos.is_noisy(m);
    if (quiet && skip_quiets) continue;
    const int history = quiet ? quiet_history(pos, m, ply) : capture_history(pos, m);

    if (!root && best_score > -MATE_BOUND) {
      if (quiet) {
        if (!in_check && depth <= 8 && moves_tried >= (3 + depth * depth) / (improving ? 1 : 2)) {
          skip_quiets = true;
          continue;
        }
        if (!in_check && depth <= 8 && static_eval + 100 + 100 * depth <= alpha) {
          skip_quiets = true;
          continue;
        }
        if (!in_check && depth <= 4 && history < -4000 * depth) continue;
        if (depth <= 8 && !pos.see_ge(m, -50 * depth)) continue;
      } else if (depth <= 8 && !pos.see_ge(m, -25 * depth * depth)) {
        continue;
      }
    }

    // Singular extension: if every other move is clearly worse than the hash move, search it deeper.
    int extension = 0;
    if (!root && m == tt_move && depth >= 8 && tte.depth >= depth - 3 && (tte.bound & BOUND_LOWER) &&
        std::abs(tt_score) < MATE_BOUND && ply < 2 * root_depth_) {
      const int singular_beta = tt_score - depth;
      frame(ply).excluded = m;
      const int s = search(pos, singular_beta - 1, singular_beta, (depth - 1) / 2, ply, cutnode);
      frame(ply).excluded = NO_MOVE;
      if (stopped_) return 0;
      if (s < singular_beta) extension = 1;
      else if (singular_beta >= beta) return singular_beta;  // several moves beat beta: multi-cut
      else if (tt_score >= beta) extension = -1;
    }

    Position next;
    if (!pos.make(m, next)) continue;
    moves_tried++;
    tt_.prefetch(next.key);
    if (net_) nnue::update(*net_, acc_[ply + 1], acc_[ply], next.dirty);
    frame(ply).move = m;
    frame(ply).piece = pos.board[move_from(m)];
    keys_[ply + 1] = next.key;
    const bool gives_check = next.in_check();
    const int new_depth = depth - 1 + extension;

    int score;
    if (moves_tried == 1) {
      score = -search(next, -beta, -alpha, new_depth, ply + 1, false);
    } else {
      int r = 0;
      if (depth >= 3 && quiet && moves_tried > 1 + pv_node) {
        r = LMR[std::min(depth, 63)][std::min(moves_tried, 63)];
        r += !pv_node;
        r += cutnode;
        r -= improving;
        r -= gives_check;
        if (m == frame(ply).killers[0] || m == frame(ply).killers[1]) r--;
        r -= history / 8192;
        r = std::clamp(r, 0, std::max(new_depth - 1, 0));
      }
      score = -search(next, -alpha - 1, -alpha, new_depth - r, ply + 1, true);
      if (score > alpha && r > 0) score = -search(next, -alpha - 1, -alpha, new_depth, ply + 1, !cutnode);
      if (score > alpha && pv_node) score = -search(next, -beta, -alpha, new_depth, ply + 1, false);
    }
    if (stopped_) return 0;

    if (score > best_score) {
      best_score = score;
      if (score > alpha) {
        alpha = score;
        best_move = m;
        if (pv_node) {
          pv_[ply][ply] = m;
          for (int k = ply + 1; k < pv_len_[ply + 1]; k++) pv_[ply][k] = pv_[ply + 1][k];
          pv_len_[ply] = std::max(pv_len_[ply + 1], ply + 1);
        }
        if (score >= beta) {
          const int bonus = history_bonus(depth);
          if (quiet) {
            Frame& f = frame(ply);
            if (f.killers[0] != m) {
              f.killers[1] = f.killers[0];
              f.killers[0] = m;
            }
            update_quiet(pos, m, ply, bonus);
            for (int q = 0; q < n_quiets; q++) update_quiet(pos, quiets[q], ply, -bonus);
          } else {
            gravity(capture_history(pos, m), bonus);
          }
          for (int c = 0; c < n_captures; c++) gravity(capture_history(pos, captures[c]), -bonus);
          break;
        }
      }
    }
    if (quiet && n_quiets < 64) quiets[n_quiets++] = m;
    if (!quiet && n_captures < 32) captures[n_captures++] = m;
  }

  if (moves_tried == 0) return excluded ? alpha : in_check ? -MATE + ply : 0;
  const int bound = best_score >= beta ? BOUND_LOWER : best_move != NO_MOVE ? BOUND_EXACT : BOUND_UPPER;
  if (!excluded) {
    if (!in_check && (best_move == NO_MOVE || !pos.is_noisy(best_move)) && std::abs(best_score) < MATE_BOUND &&
        !(bound == BOUND_LOWER && best_score <= static_eval) && !(bound == BOUND_UPPER && best_score >= static_eval))
      update_correction(pos, depth, best_score - raw_eval);
    tt_.store(pos.key, best_move != NO_MOVE ? best_move : tt_move, to_tt(best_score, ply), raw_eval, depth, bound);
  }
  return best_score;
}

int Searcher::qsearch(const Position& pos, int alpha, int beta, int ply) {
  pv_len_[ply] = ply;
  count_node();
  if (should_stop()) return 0;
  seldepth_ = std::max(seldepth_, ply);
  if (pos.halfmove >= 100 || pos.insufficient_material()) return 0;
  const bool in_check = pos.in_check();
  if (ply >= MAX_PLY - 1) return in_check ? 0 : evaluate(pos, ply);

  TTData tte{};
  const bool tt_hit = tt_.probe(pos.key, tte);
  const int tt_score = tt_hit ? from_tt(tte.score, ply) : NO_SCORE;
  if (tt_hit && tt_score != NO_SCORE && beta - alpha == 1 && bound_allows(tte.bound, tt_score, alpha, beta))
    return tt_score;

  int best = -INF, raw_eval = NO_SCORE, static_eval = NO_SCORE;
  if (!in_check) {
    raw_eval = tt_hit && tte.eval != NO_SCORE ? tte.eval : evaluate(pos, ply);
    static_eval = best = corrected(pos, raw_eval);
    if (best >= beta) return best;
    alpha = std::max(alpha, best);
  }

  MoveList list;
  pos.gen_moves(list, !in_check);  // in check we must look at every evasion
  int scores[MAX_MOVES];
  score_moves(pos, list, scores, tt_hit ? tte.move : NO_MOVE, ply);

  Move best_move = NO_MOVE;
  int legal = 0;
  for (int i = 0; i < list.size; i++) {
    pick_next(list, scores, i);
    const Move m = list.moves[i];
    if (!in_check) {
      if (!pos.see_ge(m, 0)) continue;
      if (move_flag(m) != MF_PROMO && static_eval + captured_value(pos, m) + 200 <= alpha) continue;
    }
    Position next;
    if (!pos.make(m, next)) continue;
    legal++;
    if (net_) nnue::update(*net_, acc_[ply + 1], acc_[ply], next.dirty);
    frame(ply).move = m;
    frame(ply).piece = pos.board[move_from(m)];
    keys_[ply + 1] = next.key;
    const int score = -qsearch(next, -beta, -alpha, ply + 1);
    if (stopped_) return 0;
    if (score > best) {
      best = score;
      if (score > alpha) {
        alpha = score;
        best_move = m;
        if (score >= beta) break;
      }
    }
  }
  if (in_check && legal == 0) return -MATE + ply;
  tt_.store(pos.key, best_move, to_tt(best, ply), raw_eval, 0, best >= beta ? BOUND_LOWER : BOUND_UPPER);
  return best;
}

void Searcher::report(int depth, int score) const {
  const i64 ms = elapsed_ms();
  u64 nodes = node_count();
  for (const Searcher* peer : peers) nodes += peer->node_count();
  const unsigned long long nps = ms > 0 ? (unsigned long long)(nodes * 1000 / u64(ms)) : (unsigned long long)nodes;
  std::string score_text;
  if (std::abs(score) >= MATE_BOUND) {
    const int moves = (MATE - std::abs(score) + 1) / 2;
    score_text = "mate " + std::to_string(score > 0 ? moves : -moves);
  } else {
    score_text = "cp " + std::to_string(score);
  }
  std::string pv;
  for (int i = 0; i < pv_len_[0]; i++) pv += ' ' + move_to_uci(pv_[0][i]);
  std::printf("info depth %d seldepth %d score %s nodes %llu nps %llu time %lld hashfull %d pv%s\n", depth, seldepth_,
              score_text.c_str(), (unsigned long long)nodes, nps, (long long)ms, tt_.hashfull(), pv.c_str());
  std::fflush(stdout);
}
