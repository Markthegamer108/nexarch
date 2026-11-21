// Basic types and helpers shared by the whole engine.
#pragma once

#include <bit>
#include <cstdint>

using u64 = std::uint64_t;
using u32 = std::uint32_t;
using u16 = std::uint16_t;
using u8 = std::uint8_t;
using i64 = std::int64_t;
using i32 = std::int32_t;
using i16 = std::int16_t;

enum Color : int { WHITE = 0, BLACK = 1 };
enum PieceType : int { PAWN = 0, KNIGHT = 1, BISHOP = 2, ROOK = 3, QUEEN = 4, KING = 5 };

// A piece is color * 6 + type; squares run a1 = 0 ... h8 = 63.
constexpr int NO_PIECE = 12;
constexpr int NO_SQ = 64;

constexpr int make_piece(int color, int type) { return color * 6 + type; }
constexpr int color_of(int piece) { return piece / 6; }
constexpr int type_of(int piece) { return piece % 6; }
constexpr int file_of(int sq) { return sq & 7; }
constexpr int rank_of(int sq) { return sq >> 3; }
constexpr int make_sq(int file, int rank) { return rank * 8 + file; }

enum Square : int {
  A1 = 0, B1, C1, D1, E1, F1, G1, H1,
  A8 = 56, B8, C8, D8, E8, F8, G8, H8,
};

constexpr u64 bb(int sq) { return 1ULL << sq; }
inline int popcount(u64 b) { return std::popcount(b); }
inline int lsb(u64 b) { return std::countr_zero(b); }
inline int pop_lsb(u64& b) {
  const int sq = lsb(b);
  b &= b - 1;
  return sq;
}

constexpr u64 FILE_A_BB = 0x0101010101010101ULL;
constexpr u64 FILE_H_BB = FILE_A_BB << 7;
constexpr u64 RANK_1_BB = 0xFFULL;
constexpr u64 RANK_8_BB = RANK_1_BB << 56;

// Moves pack into 16 bits: from (6) | to (6) | promotion piece (2) | flag (2).
using Move = u16;
constexpr Move NO_MOVE = 0;
constexpr Move NULL_MOVE = 65;
enum MoveFlag : int { MF_NORMAL = 0, MF_PROMO = 1, MF_EP = 2, MF_CASTLE = 3 };

constexpr Move make_move(int from, int to, int flag = MF_NORMAL, int promo = KNIGHT) {
  return Move(from | (to << 6) | ((promo - KNIGHT) << 12) | (flag << 14));
}
constexpr int move_from(Move m) { return m & 63; }
constexpr int move_to(Move m) { return (m >> 6) & 63; }
constexpr int move_flag(Move m) { return m >> 14; }
constexpr int move_promo(Move m) { return ((m >> 12) & 3) + KNIGHT; }

constexpr int MAX_PLY = 128;
constexpr int MAX_MOVES = 256;
constexpr int INF = 32000;
constexpr int MATE = 31000;
constexpr int MATE_BOUND = MATE - 2 * MAX_PLY;  // any |score| >= this is a forced mate
constexpr int NO_SCORE = 32001;

// xorshift64* — small, fast and plenty for hash keys and random openings.
struct Rng {
  u64 state;
  explicit Rng(u64 seed) : state(seed ? seed : 0x9E3779B97F4A7C15ULL) {}
  u64 next() {
    state ^= state >> 12;
    state ^= state << 25;
    state ^= state >> 27;
    return state * 2685821657736338717ULL;
  }
  u64 sparse() { return next() & next() & next(); }
  u32 below(u32 n) { return u32(next() % n); }
};

#if defined(_MSC_VER)
#include <intrin.h>
inline u64 mul_hi64(u64 a, u64 b) { return __umulh(a, b); }
inline void prefetch(const void* p) { _mm_prefetch(static_cast<const char*>(p), _MM_HINT_T0); }
#else
inline u64 mul_hi64(u64 a, u64 b) { return u64((static_cast<unsigned __int128>(a) * b) >> 64); }
inline void prefetch(const void* p) { __builtin_prefetch(p); }
#endif
