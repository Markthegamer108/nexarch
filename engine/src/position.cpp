#include "position.h"

#include <cctype>
#include <cstring>
#include <sstream>

namespace zobrist {
u64 piece[12][64], castle[16], ep[8], side;
}

namespace {

int castle_mask[64];
constexpr int SEE_VALUE[6] = {100, 300, 300, 500, 900, 0};
constexpr const char* PIECE_CHARS = "PNBRQKpnbrqk";

int see_value(int piece) { return piece == NO_PIECE ? 0 : SEE_VALUE[type_of(piece)]; }

}  // namespace

void init_zobrist() {
  Rng rng(0x4E6578617263ULL);
  for (auto& squares : zobrist::piece)
    for (u64& k : squares) k = rng.next();
  for (u64& k : zobrist::castle) k = rng.next();
  for (u64& k : zobrist::ep) k = rng.next();
  zobrist::side = rng.next();
  for (int& m : castle_mask) m = 15;
  castle_mask[A1] = 15 & ~2;
  castle_mask[E1] = 15 & ~3;
  castle_mask[H1] = 15 & ~1;
  castle_mask[A8] = 15 & ~8;
  castle_mask[E8] = 15 & ~12;
  castle_mask[H8] = 15 & ~4;
}

void Position::put(int p, int sq) {
  pcs[color_of(p)][type_of(p)] |= bb(sq);
  occ[color_of(p)] |= bb(sq);
  all |= bb(sq);
  board[sq] = u8(p);
  key ^= zobrist::piece[p][sq];
  if (type_of(p) == PAWN) pawn_key ^= zobrist::piece[p][sq];
}

void Position::remove(int p, int sq) {
  pcs[color_of(p)][type_of(p)] ^= bb(sq);
  occ[color_of(p)] ^= bb(sq);
  all ^= bb(sq);
  board[sq] = NO_PIECE;
  key ^= zobrist::piece[p][sq];
  if (type_of(p) == PAWN) pawn_key ^= zobrist::piece[p][sq];
}

void Position::move_piece(int p, int from, int to) {
  const u64 from_to = bb(from) | bb(to);
  pcs[color_of(p)][type_of(p)] ^= from_to;
  occ[color_of(p)] ^= from_to;
  all ^= from_to;
  board[from] = NO_PIECE;
  board[to] = u8(p);
  key ^= zobrist::piece[p][from] ^ zobrist::piece[p][to];
  if (type_of(p) == PAWN) pawn_key ^= zobrist::piece[p][from] ^ zobrist::piece[p][to];
}

Position Position::startpos() {
  Position pos;
  pos.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1");
  return pos;
}

bool Position::set_fen(const std::string& fen) {
  *this = Position{};
  std::memset(board, NO_PIECE, sizeof(board));
  ep = NO_SQ;
  std::istringstream in(fen);
  std::string placement, side, rights, ep_text;
  in >> placement >> side >> rights >> ep_text;
  if (!(in >> halfmove)) halfmove = 0;
  if (!(in >> fullmove)) fullmove = 1;
  if (placement.empty()) return false;

  int rank = 7, file = 0;
  for (const char c : placement) {
    if (c == '/') {
      rank--;
      file = 0;
    } else if (std::isdigit(static_cast<unsigned char>(c))) {
      file += c - '0';
    } else {
      const char* found = std::strchr(PIECE_CHARS, c);
      if (!found || file > 7 || rank < 0) return false;
      put(int(found - PIECE_CHARS), make_sq(file, rank));
      file++;
    }
  }
  if (popcount(pcs[WHITE][KING]) != 1 || popcount(pcs[BLACK][KING]) != 1) return false;

  stm = side == "b" ? BLACK : WHITE;
  castling = 0;
  for (const char c : rights) {
    if (c == 'K') castling |= 1;
    if (c == 'Q') castling |= 2;
    if (c == 'k') castling |= 4;
    if (c == 'q') castling |= 8;
  }
  // Drop castling rights that the piece placement cannot support.
  if (board[E1] != make_piece(WHITE, KING)) castling &= ~3;
  if (board[H1] != make_piece(WHITE, ROOK)) castling &= ~1;
  if (board[A1] != make_piece(WHITE, ROOK)) castling &= ~2;
  if (board[E8] != make_piece(BLACK, KING)) castling &= ~12;
  if (board[H8] != make_piece(BLACK, ROOK)) castling &= ~4;
  if (board[A8] != make_piece(BLACK, ROOK)) castling &= ~8;

  // Only keep an en passant square if a capture there is actually possible (keeps hash keys canonical).
  if (ep_text.size() == 2 && ep_text[0] >= 'a' && ep_text[0] <= 'h' && (ep_text[1] == '3' || ep_text[1] == '6')) {
    const int sq = make_sq(ep_text[0] - 'a', ep_text[1] - '1');
    if (PAWN_ATTACKS[stm ^ 1][sq] & pcs[stm][PAWN]) ep = sq;
  }
  key ^= zobrist::castle[castling];
  if (ep != NO_SQ) key ^= zobrist::ep[file_of(ep)];
  if (stm == BLACK) key ^= zobrist::side;
  return true;
}

std::string Position::fen() const {
  std::string out;
  for (int r = 7; r >= 0; r--) {
    int empty = 0;
    for (int f = 0; f < 8; f++) {
      const int p = board[make_sq(f, r)];
      if (p == NO_PIECE) {
        empty++;
        continue;
      }
      if (empty) out += char('0' + empty);
      empty = 0;
      out += PIECE_CHARS[p];
    }
    if (empty) out += char('0' + empty);
    if (r) out += '/';
  }
  out += stm == WHITE ? " w " : " b ";
  if (!castling) out += '-';
  if (castling & 1) out += 'K';
  if (castling & 2) out += 'Q';
  if (castling & 4) out += 'k';
  if (castling & 8) out += 'q';
  out += ' ';
  out += ep == NO_SQ ? "-" : square_name(ep);
  out += ' ' + std::to_string(halfmove) + ' ' + std::to_string(fullmove);
  return out;
}

bool Position::attacked(int sq, int by) const {
  if (PAWN_ATTACKS[by ^ 1][sq] & pcs[by][PAWN]) return true;
  if (KNIGHT_ATTACKS[sq] & pcs[by][KNIGHT]) return true;
  if (KING_ATTACKS[sq] & pcs[by][KING]) return true;
  const u64 diagonal = pcs[by][BISHOP] | pcs[by][QUEEN];
  if (diagonal && (bishop_attacks(sq, all) & diagonal)) return true;
  const u64 straight = pcs[by][ROOK] | pcs[by][QUEEN];
  return straight && (rook_attacks(sq, all) & straight);
}

u64 Position::attackers_to(int sq, u64 occupied) const {
  const u64 diagonal = pcs[WHITE][BISHOP] | pcs[BLACK][BISHOP] | pcs[WHITE][QUEEN] | pcs[BLACK][QUEEN];
  const u64 straight = pcs[WHITE][ROOK] | pcs[BLACK][ROOK] | pcs[WHITE][QUEEN] | pcs[BLACK][QUEEN];
  return (PAWN_ATTACKS[BLACK][sq] & pcs[WHITE][PAWN]) | (PAWN_ATTACKS[WHITE][sq] & pcs[BLACK][PAWN]) |
         (KNIGHT_ATTACKS[sq] & (pcs[WHITE][KNIGHT] | pcs[BLACK][KNIGHT])) |
         (bishop_attacks(sq, occupied) & diagonal) | (rook_attacks(sq, occupied) & straight) |
         (KING_ATTACKS[sq] & (pcs[WHITE][KING] | pcs[BLACK][KING]));
}

bool Position::insufficient_material() const {
  if (pcs[WHITE][PAWN] | pcs[BLACK][PAWN] | pcs[WHITE][ROOK] | pcs[BLACK][ROOK] | pcs[WHITE][QUEEN] | pcs[BLACK][QUEEN])
    return false;
  return popcount(pcs[WHITE][KNIGHT] | pcs[BLACK][KNIGHT] | pcs[WHITE][BISHOP] | pcs[BLACK][BISHOP]) <= 1;
}

void Position::gen_moves(MoveList& list, bool noisy_only) const {
  const int us = stm, them = us ^ 1;
  const u64 enemy = occ[them];
  const u64 targets = noisy_only ? enemy : ~occ[us];
  const int up = us == WHITE ? 8 : -8;
  const u64 last_rank = us == WHITE ? RANK_8_BB : RANK_1_BB;
  const u64 start_rank = us == WHITE ? (RANK_1_BB << 8) : (RANK_1_BB << 48);

  auto add_promotions = [&](int from, int to) {
    list.add(make_move(from, to, MF_PROMO, QUEEN));
    if (noisy_only) return;
    list.add(make_move(from, to, MF_PROMO, ROOK));
    list.add(make_move(from, to, MF_PROMO, BISHOP));
    list.add(make_move(from, to, MF_PROMO, KNIGHT));
  };

  for (u64 pawns = pcs[us][PAWN]; pawns;) {
    const int from = pop_lsb(pawns);
    const int to = from + up;
    if (!(all & bb(to))) {
      if (bb(to) & last_rank) {
        add_promotions(from, to);
      } else if (!noisy_only) {
        list.add(make_move(from, to));
        if ((bb(from) & start_rank) && !(all & bb(to + up))) list.add(make_move(from, to + up));
      }
    }
    for (u64 caps = PAWN_ATTACKS[us][from] & enemy; caps;) {
      const int target = pop_lsb(caps);
      if (bb(target) & last_rank)
        add_promotions(from, target);
      else
        list.add(make_move(from, target));
    }
    if (ep != NO_SQ && (PAWN_ATTACKS[us][from] & bb(ep))) list.add(make_move(from, ep, MF_EP));
  }

  for (u64 b = pcs[us][KNIGHT]; b;) {
    const int from = pop_lsb(b);
    for (u64 t = KNIGHT_ATTACKS[from] & targets; t;) list.add(make_move(from, pop_lsb(t)));
  }
  for (u64 b = pcs[us][BISHOP]; b;) {
    const int from = pop_lsb(b);
    for (u64 t = bishop_attacks(from, all) & targets; t;) list.add(make_move(from, pop_lsb(t)));
  }
  for (u64 b = pcs[us][ROOK]; b;) {
    const int from = pop_lsb(b);
    for (u64 t = rook_attacks(from, all) & targets; t;) list.add(make_move(from, pop_lsb(t)));
  }
  for (u64 b = pcs[us][QUEEN]; b;) {
    const int from = pop_lsb(b);
    for (u64 t = queen_attacks(from, all) & targets; t;) list.add(make_move(from, pop_lsb(t)));
  }
  const int king = king_sq(us);
  for (u64 t = KING_ATTACKS[king] & targets; t;) list.add(make_move(king, pop_lsb(t)));

  if (noisy_only || !castling) return;
  if (us == WHITE) {
    if ((castling & 1) && !(all & (bb(F1) | bb(G1))) && !attacked(E1, BLACK) && !attacked(F1, BLACK))
      list.add(make_move(E1, G1, MF_CASTLE));
    if ((castling & 2) && !(all & (bb(B1) | bb(C1) | bb(D1))) && !attacked(E1, BLACK) && !attacked(D1, BLACK))
      list.add(make_move(E1, C1, MF_CASTLE));
  } else {
    if ((castling & 4) && !(all & (bb(F8) | bb(G8))) && !attacked(E8, WHITE) && !attacked(F8, WHITE))
      list.add(make_move(E8, G8, MF_CASTLE));
    if ((castling & 8) && !(all & (bb(B8) | bb(C8) | bb(D8))) && !attacked(E8, WHITE) && !attacked(D8, WHITE))
      list.add(make_move(E8, C8, MF_CASTLE));
  }
}

bool Position::make(Move m, Position& next) const {
  next = *this;
  const int from = move_from(m), to = move_to(m), flag = move_flag(m);
  const int us = stm, them = us ^ 1;
  const int piece = board[from];
  DirtyPieces& dirty = next.dirty;
  dirty.n = 0;
  next.halfmove++;
  if (ep != NO_SQ) {
    next.key ^= zobrist::ep[file_of(ep)];
    next.ep = NO_SQ;
  }

  if (flag == MF_EP) {
    const int cap_sq = to + (us == WHITE ? -8 : 8);
    const int captured = make_piece(them, PAWN);
    next.remove(captured, cap_sq);
    dirty.add(captured, cap_sq, NO_SQ);
    next.halfmove = 0;
  } else if (board[to] != NO_PIECE) {
    const int captured = board[to];
    next.remove(captured, to);
    dirty.add(captured, to, NO_SQ);
    next.halfmove = 0;
  }

  if (flag == MF_PROMO) {
    const int promoted = make_piece(us, move_promo(m));
    next.remove(piece, from);
    next.put(promoted, to);
    dirty.add(piece, from, NO_SQ);
    dirty.add(promoted, NO_SQ, to);
    next.halfmove = 0;
  } else {
    next.move_piece(piece, from, to);
    dirty.add(piece, from, to);
    if (type_of(piece) == PAWN) {
      next.halfmove = 0;
      if (to - from == 16 || from - to == 16) {
        const int ep_sq = (from + to) / 2;
        if (PAWN_ATTACKS[us][ep_sq] & pcs[them][PAWN]) {
          next.ep = ep_sq;
          next.key ^= zobrist::ep[file_of(ep_sq)];
        }
      }
    } else if (flag == MF_CASTLE) {
      const int rook = make_piece(us, ROOK);
      const int rook_from = to > from ? to + 1 : to - 2;
      const int rook_to = to > from ? to - 1 : to + 1;
      next.move_piece(rook, rook_from, rook_to);
      dirty.add(rook, rook_from, rook_to);
    }
  }

  const int rights = castling & castle_mask[from] & castle_mask[to];
  if (rights != castling) {
    next.key ^= zobrist::castle[castling] ^ zobrist::castle[rights];
    next.castling = rights;
  }
  next.stm = them;
  next.key ^= zobrist::side;
  if (us == BLACK) next.fullmove++;
  return !next.attacked(next.king_sq(us), them);
}

void Position::make_null(Position& next) const {
  next = *this;
  next.dirty.n = 0;
  if (ep != NO_SQ) {
    next.key ^= zobrist::ep[file_of(ep)];
    next.ep = NO_SQ;
  }
  next.stm ^= 1;
  next.key ^= zobrist::side;
  next.halfmove++;
}

bool Position::see_ge(Move m, int threshold) const {
  if (move_flag(m) != MF_NORMAL) return 0 >= threshold;
  const int from = move_from(m), to = move_to(m);
  int swap = see_value(board[to]) - threshold;
  if (swap < 0) return false;
  swap = see_value(board[from]) - swap;
  if (swap <= 0) return true;

  u64 occupied = all ^ bb(from) ^ bb(to);
  int side = color_of(board[from]);
  u64 attackers = attackers_to(to, occupied);
  const u64 diagonal = pcs[WHITE][BISHOP] | pcs[BLACK][BISHOP] | pcs[WHITE][QUEEN] | pcs[BLACK][QUEEN];
  const u64 straight = pcs[WHITE][ROOK] | pcs[BLACK][ROOK] | pcs[WHITE][QUEEN] | pcs[BLACK][QUEEN];
  int res = 1;
  while (true) {
    side ^= 1;
    attackers &= occupied;
    const u64 mine = attackers & occ[side];
    if (!mine) break;
    res ^= 1;
    u64 b;
    if ((b = mine & pcs[side][PAWN])) {
      if ((swap = SEE_VALUE[PAWN] - swap) < res) break;
      occupied ^= bb(lsb(b));
      attackers |= bishop_attacks(to, occupied) & diagonal;
    } else if ((b = mine & pcs[side][KNIGHT])) {
      if ((swap = SEE_VALUE[KNIGHT] - swap) < res) break;
      occupied ^= bb(lsb(b));
    } else if ((b = mine & pcs[side][BISHOP])) {
      if ((swap = SEE_VALUE[BISHOP] - swap) < res) break;
      occupied ^= bb(lsb(b));
      attackers |= bishop_attacks(to, occupied) & diagonal;
    } else if ((b = mine & pcs[side][ROOK])) {
      if ((swap = SEE_VALUE[ROOK] - swap) < res) break;
      occupied ^= bb(lsb(b));
      attackers |= rook_attacks(to, occupied) & straight;
    } else if ((b = mine & pcs[side][QUEEN])) {
      if ((swap = SEE_VALUE[QUEEN] - swap) < res) break;
      occupied ^= bb(lsb(b));
      attackers |= (bishop_attacks(to, occupied) & diagonal) | (rook_attacks(to, occupied) & straight);
    } else {
      // Only the king is left: it may only recapture if the other side has nothing more.
      return (attackers & ~occ[side]) ? res ^ 1 : res;
    }
  }
  return res != 0;
}

std::string square_name(int sq) { return {char('a' + file_of(sq)), char('1' + rank_of(sq))}; }

std::string move_to_uci(Move m) {
  if (m == NO_MOVE) return "0000";
  std::string out = square_name(move_from(m)) + square_name(move_to(m));
  if (move_flag(m) == MF_PROMO) out += "nbrq"[move_promo(m) - KNIGHT];
  return out;
}

Move parse_uci_move(const Position& pos, const std::string& text) {
  MoveList list;
  pos.gen_moves(list, false);
  Position next;
  for (int i = 0; i < list.size; i++)
    if (move_to_uci(list.moves[i]) == text && pos.make(list.moves[i], next)) return list.moves[i];
  return NO_MOVE;
}

int count_legal(const Position& pos) {
  MoveList list;
  pos.gen_moves(list, false);
  Position next;
  int n = 0;
  for (int i = 0; i < list.size; i++) n += pos.make(list.moves[i], next);
  return n;
}
