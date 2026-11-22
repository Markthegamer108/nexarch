KAGGLE=.venv/bin/kaggle
GH=$HOME/.local/bin/gh

say() { echo "$(TZ=Europe/Berlin date '+%F %H:%M:%S') $*" >> "$LOG"; }
mem() { awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo; }

kernel_state() {
  $KAGGLE kernels status "markthegamer108/$1" 2>&1 | tail -1 | grep -o '"KernelWorkerStatus\.[A-Z_]*"' | tr -d '"' | sed 's/^KernelWorkerStatus\.//'
}

upload_dataset() {
  local slug=$1 dir=$2 msg=$3 out i ok=0
  for i in 1 2 3 4 5; do
    if $KAGGLE datasets status "markthegamer108/$slug" >/dev/null 2>&1; then
      out=$($KAGGLE datasets version -p "$dir" -m "$msg" 2>&1)
    else
      out=$($KAGGLE datasets create -p "$dir" 2>&1)
    fi
    printf '%s\n' "$out" >> "$LOG"
    if grep -q 'is being created' <<<"$out"; then ok=1; break; fi
    say "dataset $slug: upload attempt $i not accepted"
    sleep 300
  done
  [ $ok -eq 1 ] || { say "dataset $slug: UPLOAD FAILED"; return 1; }
  for i in $(seq 1 240); do
    [ "$($KAGGLE datasets status "markthegamer108/$slug" 2>&1 | tail -1)" = ready ] && { say "dataset $slug ready"; return 0; }
    sleep 30
  done
  say "dataset $slug: NOT READY after 2 h"
  return 1
}

push_kernel() {
  local name=$1 tries=$2 i st out
  shift 2
  for i in $(seq 1 "$tries"); do
    st=$(kernel_state "$name")
    case "$st" in RUNNING|QUEUED|COMPLETE) say "$name is already $st: not pushing again"; return 0 ;; esac
    out=$(env "$@" 2>&1)
    printf '%s\n' "$out" >> "$LOG"
    if grep -q 'successfully pushed' <<<"$out"; then say "launched $name"; return 0; fi
    say "push of $name not accepted (try $i/$tries): $(grep -m1 -i 'error' <<<"$out" | cut -c1-200)"
    sleep 180
  done
  say "GAVE UP launching $name"
  return 1
}

gh_collect() {
  local run=$1 s="" i
  for i in $(seq 1 600); do
    s=$($GH run view "$run" --json status,conclusion --jq '"\(.status) \(.conclusion // "")"' 2>/dev/null)
    case "$s" in completed*) break ;; esac
    [ $((i % 15)) -eq 1 ] && say "Actions run $run: ${s:-no answer}"
    sleep 120
  done
  say "Actions run $run: ${s:-no answer}"
  for i in 1 2 3 4 5; do
    rm -rf "kaggle-out/gh-$run"
    mkdir -p "kaggle-out/gh-$run"
    $GH run download "$run" -D "kaggle-out/gh-$run" >> "$LOG" 2>&1 && break
    say "gh run download $run failed (try $i)"
    sleep 120
  done
  say "Actions run $run: $(find "kaggle-out/gh-$run" -name '*.meta.npz' | wc -l) graded parts downloaded"
}

local_grade() {
  local data=$1 out=$2 log=$3 secs=$4 w=$5 skip=$6 py rc t0=0 a
  setsid nice -n 15 .venv/bin/python tools/grade.py --config nets/graders.json --data "$data" --out "$out" \
    --workers "$w" --seconds "$secs" --flush-every 20 --shard 0 --shards 1 --skip "$skip" > "$log" 2>&1 < /dev/null &
  py=$!
  say "local grading started: pid $py, $w workers, ${secs}s, MemAvailable $(mem) MB"
  while kill -0 "$py" 2>/dev/null; do
    a=$(mem)
    if [ "$t0" -eq 0 ] && [ "$a" -lt "${GUARD_MB:-1500}" ]; then
      say "MemAvailable ${a} MB: asking local grading to stop"
      kill -TERM "$py" 2>/dev/null
      t0=$(date +%s)
    elif [ "$t0" -gt 0 ] && [ $(( $(date +%s) - t0 )) -gt 180 ]; then
      say "local grading still running 180 s after SIGTERM: killing its process group"
      kill -KILL -- "-$py" 2>/dev/null
    fi
    sleep "${GUARD_POLL:-10}"
  done
  wait "$py"
  rc=$?
  kill -KILL -- "-$py" 2>/dev/null
  if [ ! -f "$out.meta.npz" ] && ls "$out".part*.rec >/dev/null 2>&1; then
    say "local grading exited (rc $rc) without output: rebuilding it from the part files"
    .venv/bin/python tools/grade.py --config nets/graders.json --data "$data" --out "$out" --finalize-only >> "$log" 2>&1
  fi
  say "local grading finished (rc $rc): $(tail -1 "$log")"
}
