// Attack tables: leapers are precomputed, sliders use magic bitboards.
#pragma once

#include "common.h"

extern u64 KNIGHT_ATTACKS[64];
extern u64 KING_ATTACKS[64];
extern u64 PAWN_ATTACKS[2][64];

struct Magic {
  u64 mask;
  u64 magic;
  u64* table;
  int shift;
};
extern Magic ROOK_MAGICS[64];
extern Magic BISHOP_MAGICS[64];

inline u64 rook_attacks(int sq, u64 occ) {
  const Magic& m = ROOK_MAGICS[sq];
  return m.table[((occ & m.mask) * m.magic) >> m.shift];
}
inline u64 bishop_attacks(int sq, u64 occ) {
  const Magic& m = BISHOP_MAGICS[sq];
  return m.table[((occ & m.mask) * m.magic) >> m.shift];
}
inline u64 queen_attacks(int sq, u64 occ) { return rook_attacks(sq, occ) | bishop_attacks(sq, occ); }

void init_bitboards();
