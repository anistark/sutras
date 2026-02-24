#!/usr/bin/env bash
# Post-install script: ensures the sutras Python CLI is globally available
# and up-to-date. Tries pipx → uv tool → pip in order.

set -euo pipefail

PACKAGE="sutras"
# ── AUTO-SYNC:MIN_VERSION ──
MIN_VERSION="0.4.1"
# ── AUTO-SYNC:END ──

# ── Version comparison ───────────────────────────────────────────────────────
# Returns 0 (true) if $1 >= $2 using semantic versioning.
version_gte() {
  # printf one version per line, sort with version-sort, take the first.
  # If the first (smallest) is $2, then $1 >= $2.
  [ "$2" = "$(printf '%s\n%s' "$1" "$2" | sort -V | head -n1)" ]
}

# Extract bare version number from "sutras, version X.Y.Z"
installed_version() {
  sutras --version 2>/dev/null | sed 's/.*version[[:space:]]*//' | tr -d '[:space:]'
}

# ── Check current installation ───────────────────────────────────────────────
NEED_INSTALL=true
NEED_UPGRADE=false

if command -v sutras &>/dev/null; then
  CUR=$(installed_version)
  if [ -n "$CUR" ] && version_gte "$CUR" "$MIN_VERSION"; then
    echo "✓ sutras CLI is up-to-date ($CUR >= $MIN_VERSION)"
    exit 0
  fi
  # Installed but too old — upgrade path
  echo "⇡ sutras CLI $CUR is older than required $MIN_VERSION, upgrading..."
  NEED_UPGRADE=true
  NEED_INSTALL=false
fi

# ── Upgrade helpers ──────────────────────────────────────────────────────────
try_pipx_upgrade() {
  if command -v pipx &>/dev/null; then
    echo "  Upgrading with pipx..."
    pipx upgrade "$PACKAGE" 2>/dev/null && return 0
    # If upgrade fails (e.g. not installed via pipx), try force-install
    pipx install --force "$PACKAGE>=$MIN_VERSION" 2>/dev/null && return 0
  fi
  return 1
}

try_uv_upgrade() {
  if command -v uv &>/dev/null; then
    echo "  Upgrading with uv..."
    uv tool upgrade "$PACKAGE" 2>/dev/null && return 0
    uv tool install --force "$PACKAGE>=$MIN_VERSION" 2>/dev/null && return 0
  fi
  return 1
}

try_pip_upgrade() {
  for pip_cmd in pip3 pip; do
    if command -v "$pip_cmd" &>/dev/null; then
      echo "  Upgrading with $pip_cmd..."
      "$pip_cmd" install --upgrade --user "$PACKAGE>=$MIN_VERSION" 2>/dev/null && return 0
      "$pip_cmd" install --upgrade --user --break-system-packages "$PACKAGE>=$MIN_VERSION" 2>/dev/null && return 0
    fi
  done
  return 1
}

# ── Install helpers ──────────────────────────────────────────────────────────
try_pipx_install() {
  if command -v pipx &>/dev/null; then
    echo "  Using pipx..."
    pipx install "$PACKAGE>=$MIN_VERSION" && return 0
  fi
  return 1
}

try_uv_install() {
  if command -v uv &>/dev/null; then
    echo "  Using uv..."
    uv tool install "$PACKAGE>=$MIN_VERSION" && return 0
  fi
  return 1
}

try_pip_install() {
  for pip_cmd in pip3 pip; do
    if command -v "$pip_cmd" &>/dev/null; then
      echo "  Using $pip_cmd --user..."
      "$pip_cmd" install --user "$PACKAGE>=$MIN_VERSION" 2>/dev/null && return 0
      "$pip_cmd" install --user --break-system-packages "$PACKAGE>=$MIN_VERSION" 2>/dev/null && return 0
    fi
  done
  return 1
}

# ── Main ─────────────────────────────────────────────────────────────────────
if $NEED_UPGRADE; then
  try_pipx_upgrade || try_uv_upgrade || try_pip_upgrade || {
    echo ""
    echo "⚠ Could not auto-upgrade sutras CLI to >=$MIN_VERSION."
    echo "  Please upgrade manually with one of:"
    echo "    pipx upgrade sutras"
    echo "    uv tool upgrade sutras"
    echo "    pip install --upgrade sutras"
    echo ""
    exit 0
  }
else
  echo "Installing sutras CLI globally..."
  try_pipx_install || try_uv_install || try_pip_install || {
    echo ""
    echo "⚠ Could not auto-install sutras CLI."
    echo "  Please install manually with one of:"
    echo "    pipx install sutras"
    echo "    uv tool install sutras"
    echo "    pip install --user sutras"
    echo ""
    exit 0
  }
fi

# Verify the result
if command -v sutras &>/dev/null; then
  echo "✓ sutras CLI ready ($(installed_version))"
fi
exit 0
