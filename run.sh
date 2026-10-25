#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Error: Python 3 is not installed. Install Python 3.10+ first."
  exit 1
fi

PYTHON_VERSION="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
if python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)'; then
  :
else
  echo "Error: Python 3.10+ is required (found $PYTHON_VERSION)."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

if [ -f .env ]; then
  set -a
  # .env should contain KEY=value lines only; do not put shell commands in it.
  source .env
  set +a
fi

exec python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
