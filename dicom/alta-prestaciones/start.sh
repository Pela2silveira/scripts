#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
elif [ -f environment.env ]; then
  set -a
  # shellcheck disable=SC1091
  source environment.env
  set +a
fi

python3 -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

PORT="${PORT:-8765}"
echo "Alta prestaciones (read-only) → http://127.0.0.1:${PORT}"
exec uvicorn app:app --host 127.0.0.1 --port "$PORT" --reload
