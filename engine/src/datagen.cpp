#include "datagen.h"

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <map>
#include <memory>
#include <mutex>
#include <sstream>
#include <thread>
#include <vector>

#include "search.h"

namespace {

using Clock = std::chrono::steady_clock;

class Args {
 public:
  explicit Args(const std::string& text) {
    std::istringstream in(text);
    std::string token;
    while (in >> token) {
      const auto eq = token.find('=');
      if (eq != std::string::npos) values_[token.substr(0, eq)] = token.substr(eq + 1);
    }
  }
  std::string str(const std::string& k, const std::string& fallback) const {
    const auto it = values_.find(k);
    return it == values_.end() ? fallback : it->second;
  }
  i64 num(const std::string& k, i64 fallback) const {
    const auto it = values_.find(k);
    return it == values_.end() ? fallback : std::stoll(it->second);
  }

 private:
  std::map<std::string, std::string> values_;
};

struct Record {
  u8 bytes[32];
};

Record pack(const Position& pos, int white_score) {
  Record r{};
  std::memcpy(r.bytes, &pos.all, 8);
  int k = 0;
  for (u64 b = pos.all; b; k++) {
    const int sq = pop_lsb(b);
    r.bytes[8 + k / 2] |= u8(pos.board[sq] << ((k & 1) * 4));
  }
  const i16 score = i16(std::clamp(white_score, -32000, 32000));
  std::memcpy(r.bytes + 24, &score, 2);
  r.bytes[27] = u8(pos.stm);
  const u16 fullmove = u16(std::min(pos.fullmove, 65535));
  std::memcpy(r.bytes + 28, &fullmove, 2);
  r.bytes[30] = u8(std::min(pos.halfmove, 255));
  return r;
}

int repetitions(const std::vector<u64>& keys, const Position& pos) {
  int count = 0;
  const int n = int(keys.size());
  for (int i = n - 2; i >= 0 && i >= n - pos.halfmove; i -= 2) count += keys[i] == pos.key;
  return count;
}

bool random_opening(Position& pos, std::vector<u64>& keys, Rng& rng, int plies) {
  for (int i = 0; i < plies; i++) {
    MoveList list;
    pos.gen_moves(list, false);
    Move legal[MAX_MOVES];
    int n = 0;
    Position next;
    for (int j = 0; j < list.size; j++)
      if (pos.make(list.moves[j], next)) legal[n++] = list.moves[j];
    if (n == 0) return false;
    keys.push_back(pos.key);
    pos.make(legal[rng.below(u32(n))], next);
    pos = next;
  }
  return count_legal(pos) > 0;
}

template <class OnMove>
int play_game(Position pos, std::vector<u64> keys, Searcher& white, Searcher& black, const Limits& limits,
              OnMove&& on_move) {
  int win_plies = 0, win_sign = 0, draw_plies = 0;
  for (int ply = 0; ply < 600; ply++) {
    if (count_legal(pos) == 0) return pos.in_check() ? (pos.stm == WHITE ? 0 : 2) : 1;
    if (pos.halfmove >= 100 || pos.insufficient_material() || repetitions(keys, pos) >= 2) return 1;
    Searcher& side = pos.stm == WHITE ? white : black;
    side.game_keys = keys;
    const SearchResult r = side.go(pos, limits);
    if (r.best == NO_MOVE) return 1;
    const int white_score = pos.stm == WHITE ? r.score : -r.score;
    if (std::abs(r.score) >= MATE_BOUND) return white_score > 0 ? 2 : 0;
    if (std::abs(white_score) >= 2000) {
      const int sign = white_score > 0 ? 1 : -1;
      win_plies = sign == win_sign ? win_plies + 1 : 1;
      win_sign = sign;
      if (win_plies >= 6) return sign > 0 ? 2 : 0;
    } else {
      win_plies = 0;
    }
    if (ply >= 80 && std::abs(white_score) <= 10) {
      if (++draw_plies >= 12) return 1;
    } else {
      draw_plies = 0;
    }
    on_move(pos, r, white_score);
    keys.push_back(pos.key);
    Position next;
    pos.make(r.best, next);
    pos = next;
  }
  return 1;
}

bool load_net(const std::string& path, nnue::Network& net) {
  if (path.empty() || path == "none") return false;
  std::string error;
  if (!net.load(path, error)) {
    std::printf("info string %s\n", error.c_str());
    std::exit(1);
  }
  return true;
}

u64 seed_from(const Args& args) {
  const i64 s = args.num("seed", 0);
  return s ? u64(s) : u64(Clock::now().time_since_epoch().count());
}

}

void run_datagen(const std::string& text) {
  const Args args(text);
  const int threads = int(std::max<i64>(1, args.num("threads", 1)));
  const u64 games = u64(args.num("games", 1'000'000'000));
  const u64 soft_nodes = u64(args.num("nodes", 5000));
  const u64 hard_nodes = u64(args.num("hardnodes", i64(soft_nodes) * 20));
  const int plies = int(args.num("plies", 8));
  const int max_open = int(args.num("openeval", 400));
  const i64 seconds = args.num("seconds", 0);
  const size_t hash_mb = size_t(args.num("hash", 16));
  const std::string out_path = args.str("out", "data.bin");
  const u64 seed = seed_from(args);
  nnue::Network net;
  const bool use_net = load_net(args.str("net", ""), net);

  std::FILE* out = std::fopen(out_path.c_str(), "ab");
  if (!out) {
    std::printf("info string cannot write %s\n", out_path.c_str());
    return;
  }
  std::printf("datagen: threads %d nodes %llu eval %s -> %s\n", threads, (unsigned long long)soft_nodes,
              use_net ? net.path.c_str() : "material", out_path.c_str());
  std::fflush(stdout);

  std::atomic<bool> stop_all{false};
  std::atomic<u64> claimed{0}, finished{0}, positions{0};
  u64 results[3] = {0, 0, 0};
  std::mutex mutex;
  const auto start = Clock::now();

  auto worker = [&](int id) {
    Rng rng(seed * 0x9E3779B97F4A7C15ULL + u64(id + 1) * 0xBF58476D1CE4E5B9ULL);
    TT tt;
    tt.resize(hash_mb);
    std::atomic<bool> never{false};
    auto searcher = std::make_unique<Searcher>(tt, never);
    searcher->print_info = false;
    if (use_net) searcher->set_network(&net);
    std::vector<Record> records;
    while (!stop_all.load() && claimed.fetch_add(1) < games) {
      Position pos;
      std::vector<u64> keys;
      while (true) {
        pos = Position::startpos();
        keys.clear();
        if (!random_opening(pos, keys, rng, plies + int(rng.below(2)))) continue;
        tt.clear();
        searcher->clear();
        searcher->game_keys = keys;
        Limits probe;
        probe.depth = 8;
        probe.nodes = 50000;
        if (std::abs(searcher->go(pos, probe).score) <= max_open) break;
      }
      records.clear();
      Limits limits;
      limits.soft_nodes = soft_nodes;
      limits.nodes = hard_nodes;
      const int result = play_game(pos, keys, *searcher, *searcher, limits,
                                   [&](const Position& p, const SearchResult& r, int white_score) {
                                     if (!p.in_check() && !p.is_noisy(r.best)) records.push_back(pack(p, white_score));
                                   });
      for (Record& rec : records) rec.bytes[26] = u8(result);
      std::lock_guard<std::mutex> lock(mutex);
      std::fwrite(records.data(), sizeof(Record), records.size(), out);
      positions += records.size();
      finished++;
      results[result]++;
    }
  };

  std::vector<std::thread> pool;
  for (int i = 0; i < threads; i++) pool.emplace_back(worker, i);
  auto report = [&](const char* label) {
    std::lock_guard<std::mutex> lock(mutex);
    const double secs = std::chrono::duration<double>(Clock::now() - start).count();
    std::printf("%s: games %llu positions %llu (%.0f pos/s) white/draw/black %llu/%llu/%llu elapsed %.0fs\n", label,
                (unsigned long long)finished.load(), (unsigned long long)positions.load(), positions.load() / std::max(secs, 1e-9),
                (unsigned long long)results[2], (unsigned long long)results[1], (unsigned long long)results[0], secs);
    std::fflush(stdout);
    std::fflush(out);
  };
  auto last_report = Clock::now();
  while (finished.load() < games) {
    std::this_thread::sleep_for(std::chrono::milliseconds(200));
    if (seconds && Clock::now() - start >= std::chrono::seconds(seconds)) stop_all = true;
    if (Clock::now() - last_report >= std::chrono::seconds(60)) {
      report("datagen");
      last_report = Clock::now();
    }
    if (stop_all) break;
  }
  for (std::thread& t : pool) t.join();
  report("datagen done");
  std::fclose(out);
}

void run_packfens(const std::string& text) {
  const Args args(text);
  const std::string out_path = args.str("out", "");
  if (out_path.empty()) {
    std::printf("packfens: give out=FILE\n");
    return;
  }
  std::FILE* out = std::fopen(out_path.c_str(), "ab");
  if (!out) {
    std::printf("packfens: cannot write %s\n", out_path.c_str());
    return;
  }
  std::vector<Record> buf;
  buf.reserve(1 << 16);
  u64 read = 0, kept = 0, bad = 0, illegal = 0, check = 0, noisy = 0;
  std::string line;
  auto legal_looking = [](const Position& p) {
    constexpr u64 BACK_RANKS = 0xFF000000000000FFull;
    return popcount(p.all) <= 32 && popcount(p.pcs[WHITE][KING]) == 1 && popcount(p.pcs[BLACK][KING]) == 1 &&
           !((p.pcs[WHITE][PAWN] | p.pcs[BLACK][PAWN]) & BACK_RANKS) &&
           !p.attacked(p.king_sq(p.stm ^ 1), p.stm);
  };
  auto square = [](char f, char r) { return (f >= 'a' && f <= 'h' && r >= '1' && r <= '8') ? (f - 'a') + (r - '1') * 8 : -1; };
  while (std::getline(std::cin, line)) {
    read++;
    const size_t t1 = line.find('\t'), t2 = t1 == std::string::npos ? t1 : line.find('\t', t1 + 1);
    if (t2 == std::string::npos) { bad++; continue; }
    std::string fen = line.substr(0, t1);
    if (std::count(fen.begin(), fen.end(), ' ') == 3) fen += " 0 1";
    const std::string move = line.substr(t1 + 1, t2 - t1 - 1);
    char* end = nullptr;
    const long score = std::strtol(line.c_str() + t2 + 1, &end, 10);
    Position pos;
    if (move.size() < 4 || end == line.c_str() + t2 + 1 || !pos.set_fen(fen)) { bad++; continue; }
    if (!legal_looking(pos)) { illegal++; continue; }
    const int from = square(move[0], move[1]), to = square(move[2], move[3]);
    if (from < 0 || to < 0 || pos.board[from] == NO_PIECE || color_of(pos.board[from]) != pos.stm) { bad++; continue; }
    if (pos.in_check()) { check++; continue; }
    const int target = pos.board[to];
    const bool capture = target != NO_PIECE && color_of(target) != pos.stm;
    const bool en_passant = type_of(pos.board[from]) == PAWN && (from & 7) != (to & 7) && target == NO_PIECE;
    if (capture || en_passant || move.size() >= 5) { noisy++; continue; }
    Record r = pack(pos, int(std::clamp<long>(score, -32000, 32000)));
    r.bytes[26] = 1;
    r.bytes[31] = 1;
    buf.push_back(r);
    kept++;
    if (buf.size() == buf.capacity()) {
      std::fwrite(buf.data(), sizeof(Record), buf.size(), out);
      buf.clear();
    }
  }
  std::fwrite(buf.data(), sizeof(Record), buf.size(), out);
  std::fclose(out);
  std::printf("packfens: %llu lines, %llu kept, skipped %llu impossible positions, %llu in check, "
              "%llu capture/promotion, %llu unreadable\n",
              (unsigned long long)read, (unsigned long long)kept, (unsigned long long)illegal, (unsigned long long)check,
              (unsigned long long)noisy, (unsigned long long)bad);
}

void run_match(const std::string& text) {
  const Args args(text);
  const int threads = int(std::max<i64>(1, args.num("threads", 1)));
  const u64 pairs = u64(std::max<i64>(1, args.num("games", 100) / 2));
  const u64 soft_nodes = u64(args.num("nodes", 5000));
  const i64 movetime = args.num("movetime", 0);
  const int plies = int(args.num("plies", 8));
  const u64 seed = seed_from(args);
  nnue::Network net_a, net_b;
  const bool use_a = load_net(args.str("a", "none"), net_a);
  const bool use_b = load_net(args.str("b", "none"), net_b);
  char budget[64];
  if (movetime > 0) std::snprintf(budget, sizeof(budget), "%lld ms per move", (long long)movetime);
  else std::snprintf(budget, sizeof(budget), "%llu nodes", (unsigned long long)soft_nodes);
  std::printf("match: A=%s vs B=%s, %llu games at %s\n", use_a ? net_a.path.c_str() : "material",
              use_b ? net_b.path.c_str() : "material", (unsigned long long)(pairs * 2), budget);
  std::fflush(stdout);

  std::atomic<u64> next_pair{0};
  u64 wins = 0, draws = 0, losses = 0;
  std::mutex mutex;

  auto worker = [&](int id) {
    Rng rng(seed + u64(id) * 7919);
    TT tt_a, tt_b;
    tt_a.resize(16);
    tt_b.resize(16);
    std::atomic<bool> never{false};
    auto a = std::make_unique<Searcher>(tt_a, never);
    auto b = std::make_unique<Searcher>(tt_b, never);
    a->print_info = b->print_info = false;
    if (use_a) a->set_network(&net_a);
    if (use_b) b->set_network(&net_b);
    Limits limits;
    if (movetime > 0) {
      limits.soft_ms = limits.hard_ms = movetime;
    } else {
      limits.soft_nodes = soft_nodes;
      limits.nodes = soft_nodes * 20;
    }
    while (next_pair.fetch_add(1) < pairs) {
      Position start;
      std::vector<u64> keys;
      do {
        start = Position::startpos();
        keys.clear();
      } while (!random_opening(start, keys, rng, plies));
      for (int game = 0; game < 2; game++) {
        tt_a.clear();
        tt_b.clear();
        a->clear();
        b->clear();
        const bool a_white = game == 0;
        const int result = play_game(start, keys, a_white ? *a : *b, a_white ? *b : *a, limits,
                                     [](const Position&, const SearchResult&, int) {});
        const int a_result = a_white ? result : 2 - result;
        std::lock_guard<std::mutex> lock(mutex);
        (a_result == 2 ? wins : a_result == 1 ? draws : losses)++;
        const u64 n = wins + draws + losses;
        if (n % 20 == 0) {
          std::printf("match: %llu games  +%llu =%llu -%llu\n", (unsigned long long)n, (unsigned long long)wins,
                      (unsigned long long)draws, (unsigned long long)losses);
          std::fflush(stdout);
        }
      }
    }
  };

  std::vector<std::thread> pool;
  for (int i = 0; i < threads; i++) pool.emplace_back(worker, i);
  for (std::thread& t : pool) t.join();

  const double n = double(wins + draws + losses);
  const double score = (wins + 0.5 * draws) / n;
  const double var = (wins * std::pow(1 - score, 2) + draws * std::pow(0.5 - score, 2) + losses * std::pow(score, 2)) / n;
  const double se = std::sqrt(var / n);
  auto elo = [](double s) { return -400.0 * std::log10(1.0 / std::clamp(s, 1e-6, 1 - 1e-6) - 1.0); };
  std::printf("match result: A +%llu =%llu -%llu  score %.1f%%  Elo %+.0f (95%%: %+.0f .. %+.0f)\n",
              (unsigned long long)wins, (unsigned long long)draws, (unsigned long long)losses, 100 * score, elo(score),
              elo(score - 1.96 * se), elo(score + 1.96 * se));
  std::fflush(stdout);
}
