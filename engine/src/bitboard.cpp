#include "bitboard.h"

u64 KNIGHT_ATTACKS[64];
u64 KING_ATTACKS[64];
u64 PAWN_ATTACKS[2][64];
Magic ROOK_MAGICS[64];
Magic BISHOP_MAGICS[64];

namespace {

u64 rook_table[102400];
u64 bishop_table[5248];

constexpr int ROOK_DIRS[4][2] = {{1, 0}, {-1, 0}, {0, 1}, {0, -1}};
constexpr int BISHOP_DIRS[4][2] = {{1, 1}, {1, -1}, {-1, 1}, {-1, -1}};

u64 slide(int sq, u64 occ, const int (*dirs)[2]) {
  u64 attacks = 0;
  for (int d = 0; d < 4; d++) {
    int r = rank_of(sq) + dirs[d][0], f = file_of(sq) + dirs[d][1];
    while (r >= 0 && r < 8 && f >= 0 && f < 8) {
      const int s = make_sq(f, r);
      attacks |= bb(s);
      if (occ & bb(s)) break;
      r += dirs[d][0];
      f += dirs[d][1];
    }
  }
  return attacks;
}

void init_magics(Magic* magics, u64* table, const int (*dirs)[2], Rng& rng) {
  static u64 occupancy[4096], reference[4096];
  static int epoch[4096];
  static int attempt = 0;
  for (int sq = 0; sq < 64; sq++) {
    const u64 edges = ((RANK_1_BB | RANK_8_BB) & ~(RANK_1_BB << (8 * rank_of(sq)))) |
                      ((FILE_A_BB | FILE_H_BB) & ~(FILE_A_BB << file_of(sq)));
    Magic& m = magics[sq];
    m.mask = slide(sq, 0, dirs) & ~edges;
    m.shift = 64 - popcount(m.mask);
    m.table = table;
    int size = 0;
    u64 subset = 0;
    do {
      occupancy[size] = subset;
      reference[size] = slide(sq, subset, dirs);
      size++;
      subset = (subset - m.mask) & m.mask;
    } while (subset);
    for (bool found = false; !found;) {
      do m.magic = rng.sparse();
      while (popcount((m.mask * m.magic) >> 56) < 6);
      attempt++;
      found = true;
      for (int i = 0; i < size; i++) {
        const unsigned idx = unsigned((occupancy[i] * m.magic) >> m.shift);
        if (epoch[idx] < attempt) {
          epoch[idx] = attempt;
          m.table[idx] = reference[i];
        } else if (m.table[idx] != reference[i]) {
          found = false;
          break;
        }
      }
    }
    table += size;
  }
}

}

void init_bitboards() {
  constexpr int KNIGHT_STEPS[8][2] = {{1, 2}, {2, 1}, {2, -1}, {1, -2}, {-1, -2}, {-2, -1}, {-2, 1}, {-1, 2}};
  constexpr int KING_STEPS[8][2] = {{1, 0}, {1, 1}, {0, 1}, {-1, 1}, {-1, 0}, {-1, -1}, {0, -1}, {1, -1}};
  for (int sq = 0; sq < 64; sq++) {
    const int r = rank_of(sq), f = file_of(sq);
    auto step = [&](int dr, int df) -> u64 {
      const int rr = r + dr, ff = f + df;
      return rr >= 0 && rr < 8 && ff >= 0 && ff < 8 ? bb(make_sq(ff, rr)) : 0;
    };
    KNIGHT_ATTACKS[sq] = KING_ATTACKS[sq] = 0;
    for (const auto& s : KNIGHT_STEPS) KNIGHT_ATTACKS[sq] |= step(s[0], s[1]);
    for (const auto& s : KING_STEPS) KING_ATTACKS[sq] |= step(s[0], s[1]);
    PAWN_ATTACKS[WHITE][sq] = step(1, -1) | step(1, 1);
    PAWN_ATTACKS[BLACK][sq] = step(-1, -1) | step(-1, 1);
  }
  Rng rng(1070372);
  init_magics(ROOK_MAGICS, rook_table, ROOK_DIRS, rng);
  init_magics(BISHOP_MAGICS, bishop_table, BISHOP_DIRS, rng);
}
