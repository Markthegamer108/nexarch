#include "tt.h"

#include <algorithm>

void TT::resize(size_t mb) {
  const size_t count = std::max<size_t>(1, mb * 1024 * 1024 / sizeof(Cluster));
  clusters_.assign(count, Cluster{});
  generation_ = 0;
}

void TT::clear() {
  std::fill(clusters_.begin(), clusters_.end(), Cluster{});
  generation_ = 0;
}

bool TT::probe(u64 key, TTData& out) const {
  const Cluster& cluster = clusters_[index(key)];
  const u16 key16 = u16(key);
  for (const Entry& e : cluster.entries) {
    if (e.key16 != key16 || (e.gen_bound & 3) == BOUND_NONE) continue;
    out.move = e.move;
    out.score = e.score;
    out.eval = e.eval;
    out.depth = e.depth;
    out.bound = e.gen_bound & 3;
    return true;
  }
  return false;
}

void TT::store(u64 key, Move move, int score, int eval, int depth, int bound) {
  Cluster& cluster = clusters_[index(key)];
  const u16 key16 = u16(key);
  Entry* target = &cluster.entries[0];
  for (Entry& e : cluster.entries) {
    if (e.key16 == key16) {
      target = &e;
      break;
    }
    if (worth(e) < worth(*target)) target = &e;
  }
  if (target->key16 == key16) {
    if (move == NO_MOVE) move = target->move;
    // Keep a much deeper result for the same position from this search unless the new one is exact.
    if (bound != BOUND_EXACT && depth + 3 < target->depth && (target->gen_bound & 0xFC) == generation_) return;
  }
  target->key16 = key16;
  target->move = move;
  target->score = i16(score);
  target->eval = i16(eval);
  target->depth = u8(std::clamp(depth, 0, 255));
  target->gen_bound = u8(generation_ | bound);
}

int TT::hashfull() const {
  const size_t sample = std::min<size_t>(1000, clusters_.size());
  int used = 0;
  for (size_t i = 0; i < sample; i++)
    for (const Entry& e : clusters_[i].entries) used += (e.gen_bound & 3) != BOUND_NONE && (e.gen_bound & 0xFC) == generation_;
  return sample ? int(used * 1000 / (3 * sample)) : 0;
}
