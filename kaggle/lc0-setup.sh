#!/bin/bash
# Build Lc0 0.32.1 with CUDA + Python bindings on a Kaggle T4 box, fetch BT4, and smoke-test both GPUs.
# Leaves: /tmp/nexarch/lc0/build/release/backends*.so and /tmp/nexarch/bt4.pb.gz
set -e
cd /tmp/nexarch
pip install -q meson ninja chess 2>&1 | grep -v -i 'notice\|warning' || true
python3-config --includes >/dev/null 2>&1 || { apt-get -qq update && apt-get -qq install -y python3-dev >/dev/null; }
[ -d lc0 ] || git clone -q --depth 1 --recurse-submodules --shallow-submodules --branch v0.32.1 https://github.com/LeelaChessZero/lc0.git lc0
cd lc0
PATH=$PATH:/usr/local/cuda/bin ./build.sh release -Dgtest=false -Dplain_cuda=true -Dcudnn=false -Dblas=false -Dopencl=false \
  -Dnative_cuda=true -Dnative_arch=false -Dpython_bindings=true > /kaggle/working/lc0-build.log 2>&1 \
  || { tail -40 /kaggle/working/lc0-build.log; exit 1; }
ls build/release/backends*.so
cd /tmp/nexarch
[ -s bt4.pb.gz ] || curl -sSfL -o bt4.pb.gz https://storage.lczero.org/files/networks-contrib/BT4-1024x15x32h-swa-6147500-policytune-332.pb.gz
ls -la bt4.pb.gz
for g in 0 1; do CUDA_VISIBLE_DEVICES=$g python3 - <<'EOF'
import sys, time
sys.path.insert(0, "/tmp/nexarch/lc0/build/release")
import backends as lc
b = lc.Backend(weights=lc.Weights("/tmp/nexarch/bt4.pb.gz"), backend="cuda-fp16")
x = [lc.GameState(fen="r1bq1rk1/pp2bppp/2n1pn2/2pp4/3P4/2PBPN2/PP1N1PPP/R2QK2R w KQ - 0 8").as_input(b) for _ in range(512)]
b.evaluate(*x)  # warm-up
t = time.time()
for _ in range(5):
    o = b.evaluate(*x)
dt = time.time() - t
print(f"GPU smoke test: q={o[0].q():+.4f} (CPU reference -0.9888), raw net {5 * 512 / dt:.0f} evals/s at batch 512")
EOF
done
