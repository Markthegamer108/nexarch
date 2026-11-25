#!/bin/bash
set -u
# SPDX-License-Identifier: MIT
# Copyright (C) 2026 Mark Ivanovskyy

set -euo pipefail
cd "$(dirname "$0")/.."
DOMAIN=${1:-showplace-immunize-output.ngrok-free.dev}
PORT=${2:-8765}
NGROK=${NGROK:-$HOME/.local/bin/ngrok}
[ -x "$NGROK" ] || NGROK=$(command -v ngrok || true)
[ -n "$NGROK" ] && [ -x "$NGROK" ] || { echo "ngrok is not installed"; exit 1; }
"$NGROK" config check >/dev/null 2>&1 || {
  echo "ngrok has no authtoken yet."
  echo "1. Sign in at https://dashboard.ngrok.com (free)"
  echo "2. Copy the token from https://dashboard.ngrok.com/get-started/your-authtoken"
  echo "3. Run: $NGROK config add-authtoken YOUR_TOKEN"
  echo "4. Claim a free static domain at https://dashboard.ngrok.com/domains"
  exit 1
}
echo "Serving the board at https://$DOMAIN"
echo "Free ngrok shows a one-time browser warning to new visitors."
exec "$NGROK" http --url="$DOMAIN" "$PORT"
