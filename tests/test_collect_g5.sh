#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
T=$(mktemp -d "${TMPDIR:-/tmp/opencode}/collect-g5.XXXXXX")
trap 'rm -f "$T/kaggle" "$T/calls"; rmdir "$T" 2>/dev/null || true' EXIT
export G5_OUTPUT_ROOT=$T/out G5_KAGGLE_CLI=$T/kaggle
export CALLS=$T/calls
cat > "$G5_KAGGLE_CLI" <<'EOF'
#!/bin/bash
set -eu
case "$2" in
  status) printf '%s has status "KernelWorkerStatus.%s"\n' "$3" "$MOCK_STATE" ;;
  output)
    printf 'download\n' >> "$CALLS"
    [[ "$MOCK_DOWNLOAD" != fail ]] || exit 7
    [[ "$4" = -p ]]
    printf '12:00:00 %s\n' "$MOCK_DOWNLOAD" > "$5/run.log"
    ;;
esac
EOF
chmod +x "$G5_KAGGLE_CLI"
OUT=$G5_OUTPUT_ROOT/nexarch-test
run() { bash kaggle/collect-g5-job.sh nexarch-test; }
export MOCK_STATE=QUEUED MOCK_DOWNLOAD=fail
[[ $(run) = QUEUED && ! -e $CALLS ]]
export MOCK_STATE=COMPLETE
if run; then exit 1; fi
[[ ! -e $OUT/collected ]]
export MOCK_DOWNLOAD='job not finished'
if run; then exit 1; fi
[[ ! -e $OUT/collected ]]
export MOCK_DOWNLOAD='job finished'
[[ $(run) = COMPLETE && $(run) = COMPLETE && $(wc -l < "$CALLS") = 3 ]]
[[ $(cat "$OUT/collected/remote-status") = COMPLETE ]]
rm -f "$OUT/collected/run.log" "$OUT/collected/remote-status" "$OUT/.collect.lock" "$OUT/collect.log" "$OUT/last-status"
rmdir "$OUT/collected" "$OUT" "$G5_OUTPUT_ROOT"
