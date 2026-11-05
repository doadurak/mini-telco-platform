#!/usr/bin/env bash
# One command to bring the whole live demo up from a cold start (after a reboot or Docker restart)
# and check it. Takes about 5-8 minutes.
#
#   bash scripts/demo_up.sh
#
# Docker Desktop must be running (Windows: start "Docker Desktop" first and wait for it).
set -uo pipefail
cd "$(dirname "$0")/.."

if ! docker info >/dev/null 2>&1; then
  echo "Docker is not running. Start Docker Desktop, wait until it is ready, then run this again."
  exit 1
fi

echo "== 1/3 Rebuilding CAPIF and starting the platform (reset_capif.sh) =="
bash scripts/reset_capif.sh 2>&1 | grep -E '^\[|register login|onboarded|published|✗|ERROR' || true

echo "== 2/3 Closing QoD sessions left from earlier runs =="
venv/bin/python -c "import sys; sys.path.insert(0,'scripts'); import demo_cli as d; \
d._close_qod_sessions('+905321234567','10.45.0.10'); d._close_qod_sessions('+905551112233','10.45.0.12')" \
  2>/dev/null || true

echo "== 3/3 Health check =="
venv/bin/python scripts/demo_check.py

# Live console for the presentation: Swagger + terminal buttons + live NEF/PCF logs
pkill -f scripts/demo_video/live_console.py 2>/dev/null || true
setsid nohup venv/bin/python scripts/demo_video/live_console.py > /tmp/live_console.log 2>&1 < /dev/null &
sleep 2
echo
echo "Live console: http://localhost:8099   (open in Chrome/Edge, press F11 for full screen)"
echo "Swagger only: http://localhost:8000/docs"
