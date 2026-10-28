#!/usr/bin/env bash
# Starts the Streamlit app. Usage: ./run.sh [port]   (default 8501; the next free port is used if busy)
set -euo pipefail
cd "$(dirname "$0")"
PORT="${1:-8501}"
while lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; do
  echo "Port $PORT is busy, trying $((PORT + 1))"
  PORT=$((PORT + 1))
done
echo "Opening http://localhost:$PORT  (press Ctrl+C in this window to stop the app)"
if [ -x ".venv/bin/streamlit" ]; then
  exec .venv/bin/streamlit run app.py --server.port "$PORT"
elif command -v conda >/dev/null 2>&1 && conda env list | awk '{print $1}' | grep -qx "fresherjobs"; then
  exec conda run --no-capture-output -n fresherjobs streamlit run app.py --server.port "$PORT"
else
  echo "No environment found. Run ./setup.sh first." >&2
  exit 1
fi
