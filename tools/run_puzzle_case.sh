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
COOKIE=""   # read from /get_version once the server is up; see cookie()
LOG="/tmp/puzzle_case.log"
SERVER_PID=""

# AGENTS.md documents .venv as the interpreter; $PYTHON overrides it. Do NOT
# silently fall back to a bare python3 -- it is unlikely to have aiohttp, and
# main.py then exits during import, which surfaces here as the thoroughly
# misleading "server failed to start".
PY_BIN="${PYTHON:-.venv/bin/python}"
if ! "$PY_BIN" -c "import aiohttp" 2>/dev/null; then
  echo "interpreter '$PY_BIN' cannot import aiohttp."
  echo "Set up .venv, or point PYTHON at one that can:  PYTHON=/path/to/python $0 ..."
  exit 1
fi

# Stop only the server this script started. Killing by port would take out a
# developer's running game, which is not this script's to kill.
cleanup() {
  if [ -n "$SERVER_PID" ] && kill -0 "$SERVER_PID" 2>/dev/null; then
    kill "$SERVER_PID" 2>/dev/null
    for _ in $(seq 1 15); do
      kill -0 "$SERVER_PID" 2>/dev/null || break
      sleep 1
    done
    kill -9 "$SERVER_PID" 2>/dev/null
  fi
}
trap cleanup EXIT INT TERM

# The app_version cookie must match Ver.ui_version_str or every path answers
# with the version-mismatch interstitial instead of the thing you asked for --
# silently, and with no mention of the version anywhere in the response.
cookie() {
  if [ -z "$COOKIE" ]; then
    local v
    v="$(curl -sS -m 15 --compressed "http://127.0.0.1:2345/get_version")"
    [ -z "$v" ] && { echo "could not read /get_version" >&2; exit 1; }
    COOKIE="app_version=$v"
  fi
  printf '%s' "$COOKIE"
}

# /new_puzzle reads the query string RAW -- it is never percent-decoded -- so
# the payload must be compact and contain no spaces. The fixture on disk is
# pretty-printed and carries runner-only keys (note/driver/expect/xfail) that
# the endpoint has no use for, so filter and re-encode rather than posting the
# file as it sits.
puzzle_payload() {
  "$PY_BIN" - "$1" <<'PY'
import json, sys
case = json.load(open(sys.argv[1]))
payload = {k: v for k, v in case.items()
           if k not in ("driver", "expect", "xfail", "note")}
text = json.dumps(payload, separators=(",", ":"))
if " " in text:
    offenders = [k for k, v in payload.items() if isinstance(v, str) and " " in v]
    sys.exit(f"payload contains a space; /new_puzzle takes the query string raw. "
             f"Offending keys: {offenders}")
print(text)
PY
}

# The engine asserts IsPortAvailable on startup with a plain bind() and no
# SO_REUSEADDR, and a lingering socket still fails that check after lsof has
# stopped reporting it. So test availability the same way the engine does
# rather than trusting lsof.
can_bind() {
  "$PY_BIN" - <<'PY'
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

if ! can_bind; then
  echo "port 2345 is already in use (pid $(lsof -ti TCP:2345 2>/dev/null | tr '\n' ' '))."
  echo "This script starts its own engine and will not kill a process it did not start."
  exit 1
fi

PAYLOAD="$(puzzle_payload "$PZ")" || exit 1

rm -f crash.json crash.log
: > "$LOG"
nohup "$PY_BIN" main.py > "$LOG" 2>&1 &
SERVER_PID=$!
started=0
for _ in $(seq 1 30); do
  can_bind || { started=1; break; }        # something is listening: ours
  kill -0 "$SERVER_PID" 2>/dev/null || break
  sleep 1
done
if [ "$started" != 1 ]; then
  echo "server failed to start"
  sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -E "^<F>" | tail -6
  exit 1
fi

curl -sS -g -m 60 --compressed -b "$(cookie)" \
  "http://127.0.0.1:2345/new_puzzle?$PAYLOAD" -o /dev/null -w "load http=%{http_code}\n"

CLIENT_OUT="/tmp/puzzle_client.log"
timeout 180 "$PY_BIN" tools/headless_client.py \
  --steps "$FRAMES" "${FLAGS[@]}" --quiet > "$CLIENT_OUT" 2>&1
grep -E "^!! ENGINE ERROR" "$CLIENT_OUT" | head -5
tail -1 "$CLIENT_OUT"

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "!! SERVER CRASHED"
  sed 's/\x1b\[[0-9;]*m//g' "$LOG" | grep -E "^<F>" | tail -12
  exit 1
fi

curl -sS -g -m 15 --compressed -b "$(cookie)" "http://127.0.0.1:2345/get_world?p=0" \
| "$PY_BIN" -c "
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
