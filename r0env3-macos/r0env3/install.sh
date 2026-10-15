#!/bin/bash
set -euo pipefail
[[ "$(uname -s)" == Darwin ]] || { echo 'macOS required.' >&2; exit 2; }
[[ "$EUID" != 0 ]] || { echo 'Do not run this installer with sudo.' >&2; exit 2; }
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
SKIP_BROWSERS=0
WITH_TIMER=0
for arg in "$@"; do
  case "$arg" in
    --skip-browsers) SKIP_BROWSERS=1 ;;
    --with-timer) WITH_TIMER=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done
command -v python3 >/dev/null || { echo 'Install Python 3.10+ (recommended 3.12) first.' >&2; exit 2; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'
if [[ ! -x "$PROJECT/.venv/bin/python" ]]; then
  python3 -m venv "$PROJECT/.venv"
fi
"$PROJECT/.venv/bin/python" -m pip install -e "$PROJECT"
if [[ "$SKIP_BROWSERS" == 0 ]]; then
  "$PROJECT/.venv/bin/python" -m playwright install firefox chromium
fi
chmod +x "$PROJECT/r0env.sh"
if [[ "$WITH_TIMER" == 1 ]]; then
  bash "$PROJECT/r0env.sh" install
fi
echo 'Installed. Run: ./r0env.sh help'
echo 'Keep this folder in place. No system settings or shell profiles were changed.'
