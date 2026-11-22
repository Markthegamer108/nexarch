#pragma once

#include <string>
#include <vector>

#include "position.h"

namespace nnue {

constexpr int INPUTS = 768;
constexpr int MAX_HIDDEN = 2048;
constexpr int QA = 255;
constexpr int QB = 64;
constexpr int SCALE = 400;

struct Network {
  int hidden = 0;
  std::vector<i16> ft_weights;
  std::vector<i16> ft_bias;
  std::vector<i16> out_weights;
  i32 out_bias = 0;
  std::string path;
  bool simd_safe = false;
  bool load(const std::string& file, std::string& error);
};

struct alignas(64) Accumulator {
  i16 v[2][MAX_HIDDEN];
};

inline int feature(int perspective, int piece, int sq) {
  const int relative = color_of(piece) == perspective ? 0 : 384;
  return relative + type_of(piece) * 64 + (perspective == WHITE ? sq : sq ^ 56);
}

void refresh(const Network& net, Accumulator& acc, const Position& pos);
void update(const Network& net, Accumulator& dst, const Accumulator& src, const DirtyPieces& dirty);
void copy(const Network& net, Accumulator& dst, const Accumulator& src);
int evaluate(const Network& net, const Accumulator& acc, int stm);
int evaluate_scalar(const Network& net, const Accumulator& acc, int stm);

}
