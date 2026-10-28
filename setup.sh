#!/usr/bin/env bash
# One-time setup for macOS (Apple Silicon or Intel).
# Creates a dedicated environment called "fresherjobs" (Conda if available, otherwise .venv),
# installs the pinned dependencies and the Playwright Chromium browser, then runs the tests.
# Your existing Conda environments are not modified.
set -euo pipefail
cd "$(dirname "$0")"
ENV_NAME="fresherjobs"

if command -v conda >/dev/null 2>&1 && [ "${USE_VENV:-0}" != "1" ]; then
  echo "==> Conda found: using a dedicated Conda environment '$ENV_NAME' (Python 3.12)"
  if conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "    Environment already exists — updating packages"
    conda run -n "$ENV_NAME" python -m pip install -r requirements.txt
  else
    conda env create -f environment.yml
  fi
  RUN=(conda run --no-capture-output -n "$ENV_NAME")
else
  PY=""
  for candidate in python3.12 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      ver=$("$candidate" -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')
      case "$ver" in 3.12|3.13) PY="$candidate"; break ;; esac
    fi
  done
  if [ -z "$PY" ]; then
    echo "ERROR: Python 3.12 or 3.13 is required. Install Miniconda (recommended) or Python 3.12 from python.org." >&2
    exit 1
  fi
  echo "==> Using $PY to create .venv"
  "$PY" -m venv .venv
  .venv/bin/python -m pip install --upgrade pip
  .venv/bin/python -m pip install -r requirements.txt
  RUN=(env PATH="$PWD/.venv/bin:$PATH")
fi

echo "==> Installing the Playwright Chromium browser (about 150 MB, one time)"
"${RUN[@]}" python -m playwright install chromium

echo "==> Running the test suite"
"${RUN[@]}" python -m pytest -q

echo
echo "Setup complete. Start the app with:  ./run.sh"
