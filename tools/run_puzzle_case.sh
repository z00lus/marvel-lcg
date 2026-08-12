#!/usr/bin/env bash
# Run one puzzle case from a clean server and print the resulting board.
#
# Loading a puzzle while a previous one is still mid-flight cascades into
# unrelated crashes, so each case gets a fresh process.
#
# Usage: tools/run_puzzle_case.sh <puzzle.json> [frames] [client flags...]
#   e.g. tools/run_puzzle_case.sh /tmp/case.json 26 --prefer Play --overpay 2 --pay-color Y
#   Default client flags are "--greedy"; pass "passive" as the only flag for
#   a client that acks frames but never answers.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PZ="${1:?usage: run_puzzle_case.sh <puzzle.json> [frames] [client flags...]}"
FRAMES="${2:-40}"
shift 2 2>/dev/null || shift 1
FLAGS=("$@")
[ ${#FLAGS[@]} -eq 0 ] && FLAGS=(--greedy)
[ "${FLAGS[0]:-}" = "passive" ] && FLAGS=(--passive)
COOKIE="app_version=0.5.9.201r"
LOG="/tmp/puzzle_case.log"

# The engine asserts IsPortAvailable on startup and dies if the socket is still
# held, and the old listener can linger past the point where lsof stops showing
# it, so free the port and retry the launch a few times rather than once.
# lsof going quiet is not enough: the engine's check is a plain bind() with no
# SO_REUSEADDR, so a lingering socket still fails it.  Test the same way it does.
can_bind() {
  .venv/bin/python - <<'PY'
import socket, sys
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    s.bind(("127.0.0.1", 2345))
except Exception:
    sys.exit(1)
finally:
    s.close()
PY
}

free_port() {
  local pids
  pids="$(lsof -ti TCP:2345 2>/dev/null)"
  [ -n "$pids" ] && kill $pids 2>/dev/null
  for _ in $(seq 1 20); do
    can_bind && return 0
    sleep 1
  done
  pids="$(lsof -ti TCP:2345 2>/dev/null)"
  [ -n "$pids" ] && kill -9 $pids 2>/dev/null
  for _ in $(seq 1 20); do
    can_bind && return 0
    sleep 1
  done
}

rm -f crash.json crash.log
started=0
for attempt in 1 2 3; do
  free_port
  sleep 1
  : > "$LOG"
  nohup .venv/bin/python main.py > "$LOG" 2>&1 &
  for _ in $(seq 1 30); do
    lsof -ti TCP:2345 >/dev/null 2>&1 && { started=1; break; }
    grep -q "IsPortAvailable" "$LOG" 2>/dev/null && break
    sleep 1
  done
  [ "$started" = 1 ] && break
done
if [ "$started" != 1 ]; then
  echo "server failed to start"
  sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -E "^<F>" | tail -6
  exit 1
fi

curl -sS -g -m 60 --compressed -b "$COOKIE" \
  "http://127.0.0.1:2345/new_puzzle?$(cat "$PZ")" -o /dev/null -w "load http=%{http_code}\n"

CLIENT_OUT="/tmp/puzzle_client.log"
timeout 180 .venv/bin/python tools/headless_client.py \
  --steps "$FRAMES" "${FLAGS[@]}" --quiet > "$CLIENT_OUT" 2>&1
grep -E "^!! ENGINE ERROR" "$CLIENT_OUT" | head -5
tail -1 "$CLIENT_OUT"

if ! lsof -ti TCP:2345 >/dev/null 2>&1; then
  echo "!! SERVER CRASHED"
  sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -E "^<F>" | tail -12
  exit 1
fi

curl -sS -g -m 15 --compressed -b "$COOKIE" "http://127.0.0.1:2345/get_world?p=0" \
| .venv/bin/python -c "
import json,sys
w=json.load(sys.stdin); p=(w.get('players') or [{}])[0]
def nm(x): return x.get('name') if isinstance(x,dict) else str(x)
print('  phase:', w.get('phase'), '| round:', w.get('round_id'))
for s in (w.get('area_schemes_main') or []):
    print('  main scheme threat:', (s.get('info') or {}).get('k_threat'))
# Cards tucked under an upgrade render as face-down entries bound to it.
bound = {}
for x in (p.get('area_hero') or []):
    b = x.get('bind_object_id') or 0
    if b and not x.get('is_face_up'): bound.setdefault(b, []).append(nm(x))
for x in (p.get('area_hero') or []):
    if not x.get('is_face_up'): continue
    i = x.get('info') or {}
    stats = ' '.join(f'{k}={i[k]}' for k in ('attack','thwart','defense','health') if i.get(k) is not None)
    under = bound.get(x.get('id'))
    print(f'   in play: {nm(x):24} {stats}' + (f'  tucked={under}' if under else ''))
for k in ('hand_cards','player_discard_pile','supports','allies','engaged_enemies','obligations_area'):
    v = p.get(k) or []
    if v: print(f'   {k}: {len(v)} {[nm(x) for x in v][:8]}')
for k in ('area_villain','area_schemes_side','area_boost'):
    v = w.get(k) or []
    if v: print(f'   {k}: {[nm(x) for x in v][:6]}')
for e in (w.get('area_villain') or []):
    i = e.get('info') or {}
    if i.get('health') is not None:
        print(f\"   enemy {nm(e)}: hp={i.get('health')} stunned={i.get('stunned',0)} confused={i.get('confused',0)}\")
"
# The engine's own log does NOT go to stdout — redirecting main.py captures almost
# nothing, so grepping $LOG for errors is close to vacuous (it only catches startup
# failures, before the Log sink is installed). Real signals, in order of reliability:
#   1. crash.json / crash.log — written by Engine.SaveCrash for exceptions that
#      reach Message.Send
#   2. "Error occurred" text pushed into a render frame (the client counts these)
#   3. the board state itself — the only thing that catches a handler that fails
#      silently, which is why every case here asserts on observable state
[ -f crash.json ] || [ -f crash.log ] && echo "  !! CRASH ARTIFACT WRITTEN (crash.json/crash.log)"
echo "  startup-only log errors: $(sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -cE '^<F>|AssertionError')"
