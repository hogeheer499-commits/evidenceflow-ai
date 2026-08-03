#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OSV="$ROOT/.tools/bin/osv-scanner"
DATABASE_DIR="$ROOT/.tools/osv-cache"

if [[ ! -x "$OSV" ]]; then
  echo "Run scripts/install-scanners.sh first." >&2
  exit 1
fi

mkdir -p "$DATABASE_DIR"
XDG_CACHE_HOME="$DATABASE_DIR" "$OSV" scan source \
  --offline-vulnerabilities \
  --download-offline-databases \
  --format=json \
  --allow-no-lockfiles \
  --recursive \
  "$ROOT" >/dev/null
echo "OSV offline database refreshed at $DATABASE_DIR"
