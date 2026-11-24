#include "nnue.h"

#include <algorithm>
#include <cstring>
#include <fstream>

#if defined(__AVX2__)
#include <immintrin.h>
#endif

namespace nnue {

bool Network::load(const std::string& file, std::string& error) {
  std::ifstream in(file, std::ios::binary);
  if (!in) {
    error = "cannot open " + file;
    return false;
  }
  char magic[4];
  u32 header[3];
  in.read(magic, 4);
  in.read(reinterpret_cast<char*>(header), sizeof(header));
  if (!in || std::memcmp(magic, "NXNN", 4) != 0) {
    error = file + " is not a Nexarch network";
    return false;
  }
  const int h = int(header[1]);
  if (header[0] != 1 || h <= 0 || h > MAX_HIDDEN || h % 16 != 0) {
    error = "unsupported network layout in " + file;
    return false;
  }
  std::vector<i16> fw(size_t(INPUTS) * h), fb(h), ow(size_t(2) * h);
  i32 ob = 0;
  in.read(reinterpret_cast<char*>(fw.data()), std::streamsize(fw.size() * sizeof(i16)));
  in.read(reinterpret_cast<char*>(fb.data()), std::streamsize(fb.size() * sizeof(i16)));
  in.read(reinterpret_cast<char*>(ow.data()), std::streamsize(ow.size() * sizeof(i16)));
  in.read(reinterpret_cast<char*>(&ob), sizeof(ob));
  if (!in) {
    error = file + " is truncated";
    return false;
  }
  hidden = h;
  ft_weights = std::move(fw);
  ft_bias = std::move(fb);
  out_weights = std::move(ow);
  out_bias = ob;
  path = file;
  simd_safe = std::all_of(out_weights.begin(), out_weights.end(), [](i16 w) { return w >= -127 && w <= 127; });
  return true;
}

void refresh(const Network& net, Accumulator& acc, const Position& pos) {
  const int h = net.hidden;
  for (int p = 0; p < 2; p++) {
    i16* a = acc.v[p];
    std::memcpy(a, net.ft_bias.data(), size_t(h) * sizeof(i16));
    for (u64 b = pos.all; b;) {
      const int sq = pop_lsb(b);
      const i16* w = &net.ft_weights[size_t(feature(p, pos.board[sq], sq)) * h];
      for (int i = 0; i < h; i++) a[i] = i16(a[i] + w[i]);
    }
  }
}

void update(const Network& net, Accumulator& dst, const Accumulator& src, const DirtyPieces& dirty) {
  const int h = net.hidden;
  for (int p = 0; p < 2; p++) {
    const i16* add[3];
    const i16* sub[3];
    int na = 0, ns = 0;
    for (int i = 0; i < dirty.n; i++) {
      if (dirty.from[i] != NO_SQ) sub[ns++] = &net.ft_weights[size_t(feature(p, dirty.piece[i], dirty.from[i])) * h];
      if (dirty.to[i] != NO_SQ) add[na++] = &net.ft_weights[size_t(feature(p, dirty.piece[i], dirty.to[i])) * h];
    }
    const i16* in = src.v[p];
    i16* out = dst.v[p];
    if (na == 1 && ns == 1) {
      for (int i = 0; i < h; i++) out[i] = i16(in[i] + add[0][i] - sub[0][i]);
    } else if (na == 1 && ns == 2) {
      for (int i = 0; i < h; i++) out[i] = i16(in[i] + add[0][i] - sub[0][i] - sub[1][i]);
    } else if (na == 2 && ns == 2) {
      for (int i = 0; i < h; i++) out[i] = i16(in[i] + add[0][i] + add[1][i] - sub[0][i] - sub[1][i]);
    } else {
      std::memcpy(out, in, size_t(h) * sizeof(i16));
      for (int k = 0; k < na; k++)
        for (int i = 0; i < h; i++) out[i] = i16(out[i] + add[k][i]);
      for (int k = 0; k < ns; k++)
        for (int i = 0; i < h; i++) out[i] = i16(out[i] - sub[k][i]);
    }
  }
}

void copy(const Network& net, Accumulator& dst, const Accumulator& src) {
  for (int p = 0; p < 2; p++) std::memcpy(dst.v[p], src.v[p], size_t(net.hidden) * sizeof(i16));
}

namespace {

int finish(const Network& net, i64 sum) {
  sum /= QA;
  sum += net.out_bias;
  return int(sum * SCALE / (QA * QB));
}

}

int evaluate_scalar(const Network& net, const Accumulator& acc, int stm) {
  const int h = net.hidden;
  const i16* us = acc.v[stm];
  const i16* them = acc.v[stm ^ 1];
  const i16* w = net.out_weights.data();
  i64 sum = 0;
  for (int i = 0; i < h; i++) {
    const i32 x = std::clamp<i32>(us[i], 0, QA);
    sum += i64(x * w[i]) * x;
  }
  for (int i = 0; i < h; i++) {
    const i32 x = std::clamp<i32>(them[i], 0, QA);
    sum += i64(x * w[h + i]) * x;
  }
  return finish(net, sum);
}

#if defined(__AVX2__)
int evaluate_cpu(const Network& net, const Accumulator& acc, int stm) {
  if (!net.simd_safe) return evaluate_scalar(net, acc, stm);
  const int h = net.hidden;
  const __m256i zero = _mm256_setzero_si256();
  const __m256i qa = _mm256_set1_epi16(QA);
  i64 total = 0;
  for (int half = 0; half < 2; half++) {
    const i16* a = acc.v[half == 0 ? stm : stm ^ 1];
    const i16* w = net.out_weights.data() + half * h;
    for (int start = 0; start < h; start += 64 * 16) {
      const int end = std::min(h, start + 64 * 16);
      __m256i sum = _mm256_setzero_si256();
      for (int i = start; i < end; i += 16) {
        __m256i x = _mm256_load_si256(reinterpret_cast<const __m256i*>(a + i));
        x = _mm256_min_epi16(_mm256_max_epi16(x, zero), qa);
        const __m256i weights = _mm256_loadu_si256(reinterpret_cast<const __m256i*>(w + i));
        sum = _mm256_add_epi32(sum, _mm256_madd_epi16(_mm256_mullo_epi16(x, weights), x));
      }
      alignas(32) i32 lanes[8];
      _mm256_store_si256(reinterpret_cast<__m256i*>(lanes), sum);
      for (const i32 lane : lanes) total += lane;
    }
  }
  return finish(net, total);
}
#else
int evaluate_cpu(const Network& net, const Accumulator& acc, int stm) { return evaluate_scalar(net, acc, stm); }
#endif

int evaluate(const Network& net, const Accumulator& acc, int stm) {
  if (gpu_enabled()) {
    const int v = evaluate_gpu(net, acc, stm);
    if (v != GPU_FAIL) return v;
  }
  return evaluate_cpu(net, acc, stm);
}

}
