// Entry point: the UCI protocol plus a few developer commands (perft, bench, datagen, match).
#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdio>
#include <iostream>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

#include "datagen.h"
#include "search.h"

namespace {

constexpr const char* ENGINE_NAME = "Nexarch 0.1";

struct Engine {
  TT tt;
  std::atomic<bool> stop{false};
  std::vector<std::unique_ptr<Searcher>> threads;  // threads[0] is the main search thread
  Searcher* searcher = nullptr;
  std::thread worker;
  nnue::Network net;
  bool use_net = false;
  Position pos = Position::startpos();
  std::vector<u64> history;  // keys of positions before `pos`
  int move_overhead = 30;

  Engine() {
    tt.resize(64);
    set_threads(1);
  }
  void set_threads(int n) {
    threads.clear();
    for (int i = 0; i < n; i++) {
      threads.push_back(std::make_unique<Searcher>(tt, stop));
      threads.back()->thread_id = i;
      threads.back()->print_info = i == 0;
    }
    searcher = threads[0].get();
    for (int i = 1; i < n; i++) searcher->peers.push_back(threads[i].get());
  }
  void wait() {
    if (worker.joinable()) worker.join();
  }
  void halt() {
    stop = true;
    wait();
    stop = false;
  }
};

u64 perft(const Position& pos, int depth) {
  MoveList list;
  pos.gen_moves(list, false);
  u64 nodes = 0;
  Position next;
  for (int i = 0; i < list.size; i++) {
    if (!pos.make(list.moves[i], next)) continue;
    nodes += depth <= 1 ? 1 : perft(next, depth - 1);
  }
  return nodes;
}

void cmd_perft(const Position& pos, int depth) {
  const auto start = std::chrono::steady_clock::now();
  MoveList list;
  pos.gen_moves(list, false);
  u64 total = 0;
  Position next;
  for (int i = 0; i < list.size; i++) {
    if (!pos.make(list.moves[i], next)) continue;
    const u64 n = depth <= 1 ? 1 : perft(next, depth - 1);
    std::printf("%s: %llu\n", move_to_uci(list.moves[i]).c_str(), (unsigned long long)n);
    total += n;
  }
  const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::printf("\nnodes %llu  time %.2fs  (%.1f Mnps)\n", (unsigned long long)total, secs, total / std::max(secs, 1e-9) / 1e6);
}

// Known move counts for tricky positions: any mismatch means a move-generation bug.
bool cmd_perftsuite(bool deep) {
  struct Case {
    const char* fen;
    int depth, deep_depth;
    u64 nodes, deep_nodes;
  };
  const Case cases[] = {
      {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", 5, 6, 4865609, 119060324},
      {"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", 4, 5, 4085603, 193690690},
      {"8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1", 5, 6, 674624, 11030083},
      {"r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1", 4, 5, 422333, 15833292},
      {"rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8", 4, 5, 2103487, 89941194},
      {"r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10", 4, 5, 3894594, 164075551},
  };
  bool ok = true;
  for (const Case& c : cases) {
    Position pos;
    pos.set_fen(c.fen);
    const int depth = deep ? c.deep_depth : c.depth;
    const u64 expected = deep ? c.deep_nodes : c.nodes;
    const auto start = std::chrono::steady_clock::now();
    const u64 got = perft(pos, depth);
    const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    const bool pass = got == expected;
    ok &= pass;
    std::printf("%s  depth %d  %llu (expected %llu)  %.2fs  %s\n", pass ? "PASS" : "FAIL", depth, (unsigned long long)got,
                (unsigned long long)expected, secs, c.fen);
    std::fflush(stdout);
  }
  std::printf("perft suite: %s\n", ok ? "all passed" : "FAILURES");
  return ok;
}

// Plays random games and checks every incrementally updated accumulator against a full rebuild.
void cmd_nnuecheck(Engine& e, int games) {
  if (!e.use_net) {
    std::printf("nnuecheck: load a network first (setoption name EvalFile value <file>)\n");
    return;
  }
  const int h = e.net.hidden;
  auto acc = std::make_unique<nnue::Accumulator[]>(3);
  Rng rng(2026);
  u64 checked = 0, mismatches = 0, flags[4] = {0, 0, 0, 0};
  for (int g = 0; g < games; g++) {
    Position pos = Position::startpos();
    nnue::refresh(e.net, acc[0], pos);
    for (int ply = 0; ply < 400; ply++) {
      MoveList list;
      pos.gen_moves(list, false);
      Move legal[MAX_MOVES];
      int n = 0;
      Position next;
      for (int i = 0; i < list.size; i++)
        if (pos.make(list.moves[i], next)) legal[n++] = list.moves[i];
      if (n == 0 || pos.halfmove >= 100) break;
      const Move m = legal[rng.below(u32(n))];
      pos.make(m, next);
      nnue::update(e.net, acc[1], acc[0], next.dirty);
      nnue::refresh(e.net, acc[2], next);
      const int fast = nnue::evaluate(e.net, acc[1], next.stm);
      bool same = fast == nnue::evaluate(e.net, acc[2], next.stm) && fast == nnue::evaluate_scalar(e.net, acc[2], next.stm);
      for (int p = 0; p < 2 && same; p++)
        for (int i = 0; i < h && same; i++) same = acc[1].v[p][i] == acc[2].v[p][i];
      checked++;
      flags[move_flag(m)]++;
      mismatches += !same;
      std::swap(acc[0], acc[1]);
      pos = next;
    }
  }
  std::printf("nnuecheck: %llu moves checked (normal %llu, promotion %llu, en passant %llu, castling %llu): %s\n",
              (unsigned long long)checked, (unsigned long long)flags[0], (unsigned long long)flags[1],
              (unsigned long long)flags[2], (unsigned long long)flags[3],
              mismatches ? (std::to_string(mismatches) + " MISMATCHES").c_str() : "all match");
  std::fflush(stdout);
}

void cmd_bench(Engine& e, int depth) {
  const char* fens[] = {
      "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
      "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
      "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
      "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
      "rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8",
      "r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10",
      "r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 8",
      "6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1",
      "8/8/8/4k3/8/8/3QK3/8 w - - 0 1",
      "2r3k1/pp3ppp/4p3/3pP3/3P4/P1R2N2/1q3PPP/3Q2K1 b - - 0 1",
  };
  u64 total = 0;
  const auto start = std::chrono::steady_clock::now();
  e.searcher->set_network(e.use_net ? &e.net : nullptr);
  e.searcher->print_info = false;
  for (const char* fen : fens) {
    Position pos;
    pos.set_fen(fen);
    e.tt.clear();
    e.searcher->clear();
    e.searcher->game_keys.clear();
    Limits limits;
    limits.depth = depth;
    const SearchResult r = e.searcher->go(pos, limits);
    total += r.nodes;
    std::printf("bench: %-8s %+6d  %10llu nodes  %s\n", move_to_uci(r.best).c_str(), r.score, (unsigned long long)r.nodes, fen);
  }
  e.searcher->print_info = true;
  const double secs = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
  std::printf("Bench: %llu nodes %.0f nps\n", (unsigned long long)total, total / std::max(secs, 1e-9));
  std::fflush(stdout);
}

void print_board(Engine& e) {
  std::string out = "\n +---+---+---+---+---+---+---+---+\n";
  for (int r = 7; r >= 0; r--) {
    for (int f = 0; f < 8; f++) {
      const int p = e.pos.board[make_sq(f, r)];
      out += std::string(" | ") + (p == NO_PIECE ? ' ' : "PNBRQKpnbrqk"[p]);
    }
    out += " | " + std::to_string(r + 1) + "\n +---+---+---+---+---+---+---+---+\n";
  }
  out += "   a   b   c   d   e   f   g   h\n\nFen: " + e.pos.fen() + "\n";
  std::printf("%s", out.c_str());
  std::fflush(stdout);
}

void cmd_eval(Engine& e) {
  e.searcher->set_network(e.use_net ? &e.net : nullptr);
  const int v = e.searcher->static_eval(e.pos);
  std::printf("eval: %d cp (side to move), %d cp (white), using %s\n", v, e.pos.stm == WHITE ? v : -v,
              e.use_net ? e.net.path.c_str() : "material");
  std::fflush(stdout);
}

void cmd_position(Engine& e, std::istringstream& in) {
  std::string token;
  in >> token;
  Position pos;
  if (token == "startpos") {
    pos = Position::startpos();
    in >> token;
  } else if (token == "fen") {
    std::string fen, part;
    while (in >> part && part != "moves") fen += part + " ";
    if (!pos.set_fen(fen)) {
      std::printf("info string invalid fen\n");
      return;
    }
    token = part;
  } else {
    return;
  }
  std::vector<u64> keys;
  if (token == "moves") {
    std::string text;
    while (in >> text) {
      const Move m = parse_uci_move(pos, text);
      if (m == NO_MOVE) {
        std::printf("info string illegal move %s\n", text.c_str());
        break;
      }
      keys.push_back(pos.key);
      Position next;
      pos.make(m, next);
      pos = next;
    }
  }
  e.pos = pos;
  e.history = keys;
}

void cmd_go(Engine& e, std::istringstream& in) {
  e.halt();
  e.stop = false;
  Limits limits;
  i64 wtime = -1, btime = -1, winc = 0, binc = 0, movetime = 0, movestogo = 0;
  bool infinite = false;
  std::string token;
  while (in >> token) {
    if (token == "wtime") in >> wtime;
    else if (token == "btime") in >> btime;
    else if (token == "winc") in >> winc;
    else if (token == "binc") in >> binc;
    else if (token == "movestogo") in >> movestogo;
    else if (token == "movetime") in >> movetime;
    else if (token == "depth") in >> limits.depth;
    else if (token == "nodes") in >> limits.nodes;
    else if (token == "infinite") infinite = true;
  }
  const i64 time_left = e.pos.stm == WHITE ? wtime : btime;
  const i64 inc = e.pos.stm == WHITE ? winc : binc;
  if (movetime > 0) {
    limits.soft_ms = limits.hard_ms = std::max<i64>(1, movetime - e.move_overhead);
  } else if (time_left >= 0 && !infinite) {
    const i64 available = std::max<i64>(1, time_left - e.move_overhead);
    const i64 moves_left = movestogo > 0 ? std::min<i64>(movestogo, 50) : 25;
    limits.hard_ms = std::max<i64>(1, available * 3 / 4);
    limits.soft_ms = std::clamp<i64>(available / moves_left + inc * 3 / 4, 1, limits.hard_ms);
    limits.hard_ms = std::min(limits.hard_ms, limits.soft_ms * 4);
  }
  // Hard cap: never think longer than 3 seconds per move
  limits.hard_ms = std::min<i64>(limits.hard_ms ? limits.hard_ms : 3000, 3000);
  limits.soft_ms = std::min<i64>(limits.soft_ms ? limits.soft_ms : 1500, 1500);
  limits.depth = std::clamp(limits.depth, 1, MAX_PLY - 1);
  for (auto& t : e.threads) {
    t->game_keys = e.history;
    t->set_network(e.use_net ? &e.net : nullptr);
  }
  e.worker = std::thread([&e, limits, root = e.pos] {
    // Lazy SMP: helpers search the same root and share discoveries through the hash table;
    // the main thread decides when to stop and which move to play.
    std::vector<std::thread> helpers;
    for (size_t i = 1; i < e.threads.size(); i++)
      helpers.emplace_back([&e, i, root] { e.threads[i]->go(root, Limits{}); });
    const SearchResult r = e.searcher->go(root, limits);
    e.stop = true;
    for (std::thread& h : helpers) h.join();
    std::printf("bestmove %s\n", move_to_uci(r.best).c_str());
    std::fflush(stdout);
  });
}

void cmd_setoption(Engine& e, std::istringstream& in) {
  std::string token, name, value;
  in >> token;  // "name"
  while (in >> token && token != "value") name += (name.empty() ? "" : " ") + token;
  while (in >> token) value += (value.empty() ? "" : " ") + token;
  e.halt();
  if (name == "Hash") {
    e.tt.resize(size_t(std::clamp(std::stoi(value), 1, 65536)));
  } else if (name == "Threads") {
    e.set_threads(std::clamp(std::stoi(value), 1, 1024));
  } else if (name == "Move Overhead") {
    e.move_overhead = std::clamp(std::stoi(value), 0, 5000);
  } else if (name == "EvalFile") {
    if (value.empty() || value == "<none>" || value == "material") {
      e.use_net = false;
      std::printf("info string using material evaluation\n");
    } else {
      std::string error;
      e.use_net = e.net.load(value, error);
      std::printf("info string %s\n", e.use_net ? ("loaded network " + value).c_str() : error.c_str());
    }
  }
  std::fflush(stdout);
}

// Returns false when the engine should exit.
bool handle(Engine& e, const std::string& line) {
  std::istringstream in(line);
  std::string cmd;
  in >> cmd;
  std::string rest;
  std::getline(in, rest);
  std::istringstream args(rest);
  if (cmd == "uci") {
    std::printf("id name %s\nid author markthegamer108\n", ENGINE_NAME);
    std::printf("option name Hash type spin default 64 min 1 max 65536\n");
    std::printf("option name Threads type spin default 1 min 1 max 1024\n");
    std::printf("option name Move Overhead type spin default 30 min 0 max 5000\n");
    std::printf("option name EvalFile type string default <none>\n");
    std::printf("uciok\n");
  } else if (cmd == "isready") {
    std::printf("readyok\n");
  } else if (cmd == "ucinewgame") {
    e.halt();
    e.tt.clear();
    for (auto& t : e.threads) t->clear();
  } else if (cmd == "position") {
    e.halt();
    cmd_position(e, args);
  } else if (cmd == "go") {
    cmd_go(e, args);
  } else if (cmd == "stop") {
    e.halt();
  } else if (cmd == "setoption") {
    cmd_setoption(e, args);
  } else if (cmd == "quit") {
    e.halt();
    return false;
  } else if (cmd == "d") {
    print_board(e);
  } else if (cmd == "eval") {
    cmd_eval(e);
  } else if (cmd == "perft") {
    int depth = 1;
    args >> depth;
    cmd_perft(e.pos, depth);
  } else if (cmd == "perftsuite") {
    std::string mode;
    args >> mode;
    cmd_perftsuite(mode == "deep");
  } else if (cmd == "bench") {
    int depth = 10;
    args >> depth;
    e.halt();
    cmd_bench(e, depth);
  } else if (cmd == "nnuecheck") {
    int games = 200;
    args >> games;
    cmd_nnuecheck(e, games);
  } else if (cmd == "datagen") {
    e.halt();
    run_datagen(rest);
  } else if (cmd == "match") {
    e.halt();
    run_match(rest);
  } else if (!cmd.empty()) {
    std::printf("info string unknown command %s\n", cmd.c_str());
  }
  std::fflush(stdout);
  return true;
}

}  // namespace

int main(int argc, char** argv) {
  init_bitboards();
  init_zobrist();
  Engine engine;
  if (argc > 1) {  // run one command from the command line, e.g. `nexarch bench` or `nexarch perftsuite`
    std::string line;
    for (int i = 1; i < argc; i++) line += std::string(i > 1 ? " " : "") + argv[i];
    if (line.rfind("perftsuite", 0) == 0) return cmd_perftsuite(line.find("deep") != std::string::npos) ? 0 : 1;
    handle(engine, line);
    engine.halt();
    return 0;
  }
  std::string line;
  while (std::getline(std::cin, line))
    if (!handle(engine, line)) return engine.halt(), 0;
  engine.wait();  // input closed (e.g. a piped script): let the last search finish
  return 0;
}
