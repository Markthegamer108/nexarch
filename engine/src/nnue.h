// NNUE evaluation: (768 -> H) x 2 perspectives -> 1, SCReLU activation, integer weights for fast CPU inference.
// The feature transformer is updated incrementally as pieces move, so most of the network costs almost nothing.
#pragma once

#include <string>
#include <vector>

#include "position.h"

namespace nnue {

constexpr int INPUTS = 768;
constexpr int MAX_HIDDEN = 2048;
constexpr int QA = 255;    // feature-transformer quantisation
constexpr int QB = 64;     // output-layer quantisation
constexpr int SCALE = 400; // network output units -> centipawns

struct Network {
  int hidden = 0;
  std::vector<i16> ft_weights;   // [INPUTS][hidden]
  std::vector<i16> ft_bias;      // [hidden]
  std::vector<i16> out_weights;  // [2 * hidden]: side to move first, then the opponent
  i32 out_bias = 0;
  std::string path;
  bool simd_safe = false;  // output weights fit the 16-bit SIMD fast path (|w| <= 127)
  bool load(const std::string& file, std::string& error);
};

struct alignas(64) Accumulator {
  i16 v[2][MAX_HIDDEN];  // one half per perspective (white, black)
};

// Feature index of a piece as seen from one side: own pieces first, board flipped for black.
inline int feature(int perspective, int piece, int sq) {
  const int relative = color_of(piece) == perspective ? 0 : 384;
  return relative + type_of(piece) * 64 + (perspective == WHITE ? sq : sq ^ 56);
}

void refresh(const Network& net, Accumulator& acc, const Position& pos);
void update(const Network& net, Accumulator& dst, const Accumulator& src, const DirtyPieces& dirty);
void copy(const Network& net, Accumulator& dst, const Accumulator& src);
int evaluate(const Network& net, const Accumulator& acc, int stm);         // SIMD when available
int evaluate_scalar(const Network& net, const Accumulator& acc, int stm);  // reference implementation

}  // namespace nnue
