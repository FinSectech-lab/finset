#!/bin/bash
set -euo pipefail
PROJECT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$PROJECT/r0env.sh" uninstall
echo 'LaunchAgent removed. Project, snapshots, browser cache and host settings retained.'
echo 'Use restore with a snapshot before deleting the project if you need to undo host changes.'
