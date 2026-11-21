// Board state, move generation and move making (copy-make: every move produces a new Position).
#pragma once

#include <string>

#include "bitboard.h"

struct MoveList {
  Move moves[MAX_MOVES];
  int size = 0;
  void add(Move m) { moves[size++] = m; }
};

// Pieces changed by the last move, so the NNUE accumulator can be updated instead of rebuilt.
struct DirtyPieces {
  int n = 0;
  int piece[3], from[3], to[3];  // from == NO_SQ: piece appeared; to == NO_SQ: piece removed
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
  int stm, castling, ep, halfmove, fullmove;  // castling bits: 1 = K, 2 = Q, 4 = k, 8 = q
  u64 key;
  u64 pawn_key;  // hash of the pawns alone (used by correction history)
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

  void gen_moves(MoveList& list, bool noisy_only) const;  // pseudo-legal; make() rejects illegal ones
  bool make(Move m, Position& next) const;                // false if the move leaves our king in check
  void make_null(Position& next) const;
  bool see_ge(Move m, int threshold) const;  // static exchange: does this capture sequence gain >= threshold?

 private:
  void put(int p, int sq);
  void remove(int p, int sq);
  void move_piece(int p, int from, int to);
};

void init_zobrist();
std::string square_name(int sq);
std::string move_to_uci(Move m);
Move parse_uci_move(const Position& pos, const std::string& text);  // NO_MOVE if not legal here
int count_legal(const Position& pos);
