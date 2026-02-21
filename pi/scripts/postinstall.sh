#!/usr/bin/env bash
# Post-install script: ensures the sutras Python CLI is globally available.
# Tries pipx → uv tool → pip (with --user fallback) in order.

set -euo pipefail

PACKAGE="sutras"
MIN_VERSION="0.4.1"

# Already installed and on PATH?
if command -v sutras &>/dev/null; then
  echo "✓ sutras CLI already installed ($(sutras --version 2>/dev/null || echo 'unknown version'))"
  exit 0
fi

echo "Installing sutras CLI globally..."

# 1) pipx (preferred — isolated venv, no system pollution)
if command -v pipx &>/dev/null; then
  echo "  Using pipx..."
  pipx install "$PACKAGE>=$MIN_VERSION" && exit 0
  echo "  pipx install failed, trying next method..."
fi

# 2) uv tool install
if command -v uv &>/dev/null; then
  echo "  Using uv..."
  uv tool install "$PACKAGE>=$MIN_VERSION" && exit 0
  echo "  uv tool install failed, trying next method..."
fi

# 3) pip / pip3 with --user
for pip_cmd in pip3 pip; do
  if command -v "$pip_cmd" &>/dev/null; then
    echo "  Using $pip_cmd --user..."
    "$pip_cmd" install --user "$PACKAGE>=$MIN_VERSION" 2>/dev/null && exit 0
    # Some systems block even --user; try --break-system-packages as last resort
    "$pip_cmd" install --user --break-system-packages "$PACKAGE>=$MIN_VERSION" 2>/dev/null && exit 0
  fi
done

echo ""
echo "⚠ Could not auto-install sutras CLI."
echo "  Please install manually with one of:"
echo "    pipx install sutras"
echo "    uv tool install sutras"
echo "    pip install --user sutras"
echo ""
# Don't fail the npm install — the extension will show a warning at runtime
exit 0
