// Transposition table: 32-byte buckets holding three 10-byte entries.
#pragma once

#include <vector>

#include "common.h"

enum Bound : int { BOUND_NONE = 0, BOUND_UPPER = 1, BOUND_LOWER = 2, BOUND_EXACT = 3 };

struct TTData {
  Move move;
  int score, eval, depth, bound;
};

class TT {
 public:
  void resize(size_t mb);
  void clear();
  void new_search() { generation_ = u8(generation_ + 4); }
  bool probe(u64 key, TTData& out) const;
  void store(u64 key, Move move, int score, int eval, int depth, int bound);
  void prefetch(u64 key) const { ::prefetch(&clusters_[index(key)]); }
  int hashfull() const;

 private:
  struct Entry {
    u16 key16;
    Move move;
    i16 score;
    i16 eval;
    u8 depth;
    u8 gen_bound;  // generation in the top 6 bits, bound in the low 2
  };
  struct Cluster {
    Entry entries[3];
    u16 padding;
  };
  static_assert(sizeof(Entry) == 10 && sizeof(Cluster) == 32);

  size_t index(u64 key) const { return size_t(mul_hi64(key, clusters_.size())); }
  int worth(const Entry& e) const { return int(e.depth) - 4 * (u8(generation_ - (e.gen_bound & 0xFC)) >> 2); }

  std::vector<Cluster> clusters_;
  u8 generation_ = 0;
};
