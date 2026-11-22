#pragma once

#include <string>

#include "bitboard.h"

struct MoveList {
  Move moves[MAX_MOVES];
  int size = 0;
  void add(Move m) { moves[size++] = m; }
};

struct DirtyPieces {
  int n = 0;
  int piece[3], from[3], to[3];
  void add(int p, int f, int t) {
    piece[n] = p;
    from[n] = f;
    to[n] = t;
    n++;
  }
};

namespace zobrist {
extern u64 piece[12][64], castle[16], ep[8], side;
}

struct Position {
  u64 pcs[2][6];
  u64 occ[2];
  u64 all;
  u8 board[64];
  int stm, castling, ep, halfmove, fullmove;
  u64 key;
  u64 pawn_key;
  DirtyPieces dirty;

  static Position startpos();
  bool set_fen(const std::string& fen);
  std::string fen() const;

  int king_sq(int c) const { return lsb(pcs[c][KING]); }
  bool attacked(int sq, int by) const;
  u64 attackers_to(int sq, u64 occupied) const;
  bool in_check() const { return attacked(king_sq(stm), stm ^ 1); }
  bool has_non_pawn(int c) const { return (pcs[c][KNIGHT] | pcs[c][BISHOP] | pcs[c][ROOK] | pcs[c][QUEEN]) != 0; }
  bool is_capture(Move m) const { return board[move_to(m)] != NO_PIECE || move_flag(m) == MF_EP; }
  bool is_noisy(Move m) const { return is_capture(m) || (move_flag(m) == MF_PROMO && move_promo(m) == QUEEN); }
  bool insufficient_material() const;

  void gen_moves(MoveList& list, bool noisy_only) const;
  bool make(Move m, Position& next) const;
  void make_null(Position& next) const;
  bool see_ge(Move m, int threshold) const;

 private:
  void put(int p, int sq);
  void remove(int p, int sq);
  void move_piece(int p, int from, int to);
};

void init_zobrist();
std::string square_name(int sq);
std::string move_to_uci(Move m);
Move parse_uci_move(const Position& pos, const std::string& text);
int count_legal(const Position& pos);
