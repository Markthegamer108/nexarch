#!/bin/bash
set -u
cd "$(dirname "$0")/.."
LOG=kaggle-out/pull-aws-selfplay.log
mkdir -p kaggle-out data/aws-raw
. kaggle/lib.sh
KEY=${AWS_KEY:-$HOME/.ssh/nexarch-lightsail.pem}
HOST=${AWS_HOST:-ubuntu@51.20.43.92}
DAY=${1:-$(TZ=Europe/Berlin date '+%F')}
TAG=${DAY//-/}
say "pulling AWS self-play for $DAY from $HOST"

ssh -i "$KEY" -o BatchMode=yes -o ConnectTimeout=15 "$HOST" "mkdir -p ~/nexarch/data/aws-shipped && ls ~/nexarch/data/aws/*.bin 2>/dev/null" \
  > kaggle-out/aws-chunks.txt || { say "cannot reach $HOST"; exit 1; }
N=$(grep -c '\.bin$' kaggle-out/aws-chunks.txt || true)
[ "$N" -gt 0 ] || { say "no chunks on the box yet"; exit 0; }
say "$N chunk(s) on the box"

rsync -a --remove-source-files --include 'sp-*.bin' --exclude '*.open' --exclude '*' \
  -e "ssh -i $KEY -o BatchMode=yes" \
  "$HOST:~/nexarch/data/aws/" data/aws-raw/ >> "$LOG" 2>&1 || { say "rsync failed"; exit 1; }
have=$(ls data/aws-raw/sp-*.bin 2>/dev/null | wc -l)
[ "$have" -gt 0 ] || { say "no chunks arrived"; exit 0; }

OUT=data/aws-raw/selfplay-aws-$DAY.bin
rm -f "$OUT"
for f in $(ls data/aws-raw/sp-*.bin | sort); do cat "$f" >> "$OUT"; done
POS=$(( $(stat -c %s "$OUT") / 32 ))
say "merged $have chunk(s): $POS positions -> $OUT"

D=$HOME/.cache/nexarch-kds/nexarch-selfplay-aws-$DAY
mkdir -p "$D"
ln -f "$OUT" "$D/selfplay-aws-$DAY.bin" 2>/dev/null || cp "$OUT" "$D/selfplay-aws-$DAY.bin"
printf '{"title":"nexarch-selfplay-aws-%s","id":"markthegamer108/nexarch-selfplay-aws-%s","licenses":[{"name":"MIT"}]}\n' "$DAY" "$DAY" > "$D/dataset-metadata.json"
upload_dataset nexarch-selfplay-aws-$DAY "$D" "Nexarch Gen 4 self-play from the AWS box, $DAY, $POS positions" \
  || { say "upload failed, chunks kept in data/aws-raw"; exit 1; }

for f in $(ls data/aws-raw/sp-*.bin | sort); do rm -f "$f"; done
say "done: markthegamer108/nexarch-selfplay-aws-$DAY, $POS positions, raw chunks cleared"
