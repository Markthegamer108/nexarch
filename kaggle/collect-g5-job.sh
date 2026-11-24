#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${1:?kernel name}
[[ $NAME =~ ^nexarch-[a-z0-9-]+$ ]] || exit 2
KAGGLE=${G5_KAGGLE_CLI:-.venv/bin/kaggle}
OUT=${G5_OUTPUT_ROOT:-kaggle-out}/$NAME
mkdir -p "$OUT"
exec 9>"$OUT/.collect.lock"
flock -n 9 || exit 0

if [[ -f $OUT/collected/remote-status ]]; then
  cat "$OUT/collected/remote-status"
  exit 0
fi

REF=markthegamer108/$NAME
if ! R=$(timeout 40 "$KAGGLE" kernels status "$REF" 2>&1) || [[ ! $R =~ KernelWorkerStatus\.([A-Z_]+) ]]; then
  printf '%s status unavailable: %s\n' "$(date -Is)" "$R" >> "$OUT/collect.log"
  exit 1
fi
STATE=${BASH_REMATCH[1]}
if [[ ! -f $OUT/last-status || $(cat "$OUT/last-status") != "$STATE" ]]; then
  printf '%s %s\n' "$(date -Is)" "$STATE" >> "$OUT/collect.log"
  printf '%s\n' "$STATE" > "$OUT/last-status.new"
  mv "$OUT/last-status.new" "$OUT/last-status"
fi
case "$STATE" in
  COMPLETE|ERROR|CANCELLED|CANCELED|FAILED)
    STAGE=$OUT/.download
    mkdir -p "$STAGE"
    timeout 360 "$KAGGLE" kernels output "$REF" -p "$STAGE" -o -q >> "$OUT/collect.log" 2>&1
    if [[ $STATE = COMPLETE ]]; then
      test -s "$STAGE/run.log"
      if ! grep -q ' job finished$' "$STAGE/run.log"; then
        if find "$STAGE" -maxdepth 2 \( -name 'g5-a.pt' -o -name 'g5-b.pt' -o -name 'nexarch-g5.pt' \) -print -quit | grep -q .; then
          STATE=COMPLETE_PARTIAL
        else
          exit 1
        fi
      fi
    fi
    printf '%s\n' "$STATE" > "$STAGE/remote-status"
    mv -T "$STAGE" "$OUT/collected"
    ;;
esac
printf '%s\n' "$STATE"
