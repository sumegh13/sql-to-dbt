#!/usr/bin/env bash
# Start the migration web app in the dev container / Codespace. Safe to run any number of times:
# installs what's missing, then starts the app in the background unless it's already answering.
# Everything is logged to /tmp/app.log.  Manual use:  bash .devcontainer/start.sh
set -u
LOG=/tmp/app.log
PORT="${PORT:-8000}"
export PATH="$HOME/.local/bin:$PATH"
cd "$(dirname "$0")/.."

say() { echo "$(date +%H:%M:%S) $*" | tee -a "$LOG"; }

if curl -s -m 3 -o /dev/null "http://127.0.0.1:$PORT/"; then
  say "app already running on port $PORT"
  exit 0
fi

# a stopped (Ctrl+Z) or hung copy holds the port without answering: clear it. A stopped process ignores
# SIGTERM until resumed, so resume it first, and force-kill anything still alive after 5s.
if pgrep -f "python -m app" >/dev/null; then
  say "clearing a stuck copy of the app"
  pkill -CONT -f "python -m app"; pkill -TERM -f "python -m app"
  for _ in 1 2 3 4 5; do pgrep -f "python -m app" >/dev/null || break; sleep 1; done
  pkill -KILL -f "python -m app" 2>/dev/null
  sleep 1
fi

command -v uv >/dev/null || { say "installing uv"; pip install --user --quiet uv >>"$LOG" 2>&1; }
say "syncing dependencies"
uv sync >>"$LOG" 2>&1 || { say "uv sync failed, see $LOG"; exit 1; }

say "starting app on port $PORT"
HOST=0.0.0.0 PORT="$PORT" setsid nohup uv run python -m app >>"$LOG" 2>&1 < /dev/null &

for _ in $(seq 1 30); do
  if curl -s -m 2 -o /dev/null "http://127.0.0.1:$PORT/"; then
    say "app is up: open the Ports tab and click the globe icon next to port $PORT"
    exit 0
  fi
  sleep 1
done
say "app did not answer within 30s, last log lines:"
tail -20 "$LOG"
exit 1
