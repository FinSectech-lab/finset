#!/bin/bash
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ ! -x "$PROJECT/.venv/bin/python" ]]; then
  echo 'Run bash install.sh first.' >&2
  exit 2
fi
cd "$PROJECT"
exec "$PROJECT/.venv/bin/python" -m r0env "$@"
