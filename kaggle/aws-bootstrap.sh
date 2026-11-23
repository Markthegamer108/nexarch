#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
REPO=https://github.com/Markthegamer108/nexarch.git
USER_NAME=$(id -un)
ROOT=$(pwd)
if command -v apt-get >/dev/null; then
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq build-essential git curl zstd
elif command -v dnf >/dev/null; then
  sudo dnf install -y -q gcc gcc-c++ make git curl zstd
fi
if [ ! -d .git ]; then
  cd ..
  rm -rf nexarch.tmp
  git clone -q "$REPO" nexarch.tmp
  cp -a nexarch/. nexarch.tmp/ 2>/dev/null || true
  rm -rf nexarch
  mv nexarch.tmp nexarch
  cd nexarch
else
  git fetch -q --depth 1 origin main
  git reset -q --hard origin/main
fi
make -C engine -j"$(nproc)"
chmod +x kaggle/aws-selfplay-run.sh
mkdir -p data/aws kaggle-out
sudo tee /etc/systemd/system/nexarch-selfplay.service >/dev/null <<EOF
[Unit]
Description=Nexarch self-play
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER_NAME
WorkingDirectory=$ROOT
ExecStart=$ROOT/kaggle/aws-selfplay-run.sh
Restart=always
RestartSec=15
Nice=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now nexarch-selfplay
sleep 5
systemctl --no-pager --lines=0 status nexarch-selfplay
echo "self-play service started in $ROOT as $USER_NAME"
