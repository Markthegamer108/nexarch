
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "binpack.h"

namespace {

constexpr std::int16_t VALUE_NONE = 32002;

std::string arg(int argc, char** argv, const std::string& key, const std::string& fallback) {
  for (int i = 3; i < argc; i++) {
    const std::string a = argv[i];
    if (a.rfind(key + "=", 0) == 0) return a.substr(key.size() + 1);
  }
  return fallback;
}

void pack(const binpack::TrainingDataEntry& e, unsigned char out[32]) {
  std::memset(out, 0, 32);
  const std::uint64_t occ = e.pos.piecesBB().bits();
  std::memcpy(out, &occ, 8);
  int k = 0;
  for (std::uint64_t b = occ; b; b &= b - 1, k++) {
    const int sq = __builtin_ctzll(b);
    const chess::Piece p = e.pos.pieceAt(chess::Square(sq));
    const int code = int(chess::ordinal(p.color())) * 6 + int(chess::ordinal(p.type()));
    out[8 + k / 2] |= std::uint8_t(code << ((k & 1) * 4));
  }
  const bool white = e.pos.sideToMove() == chess::Color::White;
  const long cp = std::lround(double(e.score) * 100.0 / 208.0);
  const std::int16_t score = std::int16_t(std::clamp<long>(white ? cp : -cp, -32000, 32000));
  std::memcpy(out + 24, &score, 2);
  const int result = white ? e.result : -e.result;
  out[26] = std::uint8_t(result + 1);
  out[27] = white ? 0 : 1;
  const std::uint16_t fullmove = std::uint16_t(std::min(e.ply / 2 + 1, 65535));
  std::memcpy(out + 28, &fullmove, 2);
  out[30] = e.pos.rule50Counter();
}

}

int main(int argc, char** argv) {
  if (argc < 3) {
    std::fprintf(stderr, "usage: binpack2nexarch IN.binpack OUT.bin [every=N] [offset=K] [max=M] [filter=0|1] [fens=FILE]\n");
    return 2;
  }
  const std::uint64_t every = std::max<std::uint64_t>(1, std::stoull(arg(argc, argv, "every", "1")));
  const std::uint64_t offset = std::stoull(arg(argc, argv, "offset", "0")) % every;
  const std::uint64_t max = std::stoull(arg(argc, argv, "max", "0"));
  const bool filter = arg(argc, argv, "filter", "1") != "0";
  const std::string fens_path = arg(argc, argv, "fens", "");

  std::FILE* out = std::fopen(argv[2], "wb");
  if (!out) {
    std::fprintf(stderr, "cannot write %s\n", argv[2]);
    return 1;
  }
  std::FILE* fens = fens_path.empty() ? nullptr : std::fopen(fens_path.c_str(), "w");
  binpack::CompressedTrainingDataEntryReader reader(argv[1], std::ios_base::in);

  std::vector<unsigned char> buf;
  buf.reserve(32u << 16);
  std::uint64_t seen = 0, sampled = 0, kept = 0, none = 0, check = 0, noisy = 0;
  while (reader.hasNext()) {
    const binpack::TrainingDataEntry e = reader.next();
    if (seen++ % every != offset) continue;
    sampled++;
    if (e.score == VALUE_NONE) { none++; continue; }
    if (filter && e.isInCheck()) { check++; continue; }
    if (filter && (e.isCapturingMove() || e.move.type == chess::MoveType::Promotion || e.move.type == chess::MoveType::EnPassant)) {
      noisy++;
      continue;
    }
    unsigned char rec[32];
    pack(e, rec);
    buf.insert(buf.end(), rec, rec + 32);
    if (fens && kept < 5000) std::fprintf(fens, "%s | %d | %d\n", e.pos.fen().c_str(), int(e.score), int(e.result));
    kept++;
    if (buf.size() >= (32u << 16)) {
      std::fwrite(buf.data(), 1, buf.size(), out);
      buf.clear();
    }
    if (kept % 10000000 == 0) {
      std::fprintf(stderr, "binpack2nexarch: %llu read, %llu kept\n", (unsigned long long)seen, (unsigned long long)kept);
    }
    if (max && kept >= max) break;
  }
  std::fwrite(buf.data(), 1, buf.size(), out);
  std::fclose(out);
  if (fens) std::fclose(fens);
  std::fprintf(stderr,
               "binpack2nexarch: %llu positions read, %llu sampled, %llu kept "
               "(skipped: %llu marked, %llu in check, %llu capture/promotion)\n",
               (unsigned long long)seen, (unsigned long long)sampled, (unsigned long long)kept,
               (unsigned long long)none, (unsigned long long)check, (unsigned long long)noisy);
  return 0;
}
