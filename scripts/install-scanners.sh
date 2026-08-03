#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOOLS_DIR="$ROOT/.tools"
BIN_DIR="$TOOLS_DIR/bin"
CACHE_DIR="$TOOLS_DIR/cache"
mkdir -p "$BIN_DIR" "$CACHE_DIR"

OSV_VERSION="2.4.0"
OSV_SHA256="15314940c10d26af9c6649f150b8a47c1262e8fc7e17b1d1029b0e479e8ed8a0"
OSV_FILE="$CACHE_DIR/osv-scanner_linux_amd64"
OSV_URL="https://github.com/google/osv-scanner/releases/download/v${OSV_VERSION}/osv-scanner_linux_amd64"

GITLEAKS_VERSION="8.30.1"
GITLEAKS_SHA256="551f6fc83ea457d62a0d98237cbad105af8d557003051f41f3e7ca7b3f2470eb"
GITLEAKS_FILE="$CACHE_DIR/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
GITLEAKS_URL="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"

curl --fail --location --silent --show-error "$OSV_URL" --output "$OSV_FILE"
printf '%s  %s\n' "$OSV_SHA256" "$OSV_FILE" | sha256sum --check --status
install -m 0755 "$OSV_FILE" "$BIN_DIR/osv-scanner"

curl --fail --location --silent --show-error "$GITLEAKS_URL" --output "$GITLEAKS_FILE"
printf '%s  %s\n' "$GITLEAKS_SHA256" "$GITLEAKS_FILE" | sha256sum --check --status
tar -xzf "$GITLEAKS_FILE" -C "$BIN_DIR" gitleaks
chmod 0755 "$BIN_DIR/gitleaks"

"$BIN_DIR/osv-scanner" --version
"$BIN_DIR/gitleaks" version
