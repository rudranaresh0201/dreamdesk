#!/usr/bin/env bash
# Runs the probe on a private display, D-Bus session, HOME and settings backend.
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
TMP="$(mktemp -d)"
export HOME="$TMP" XDG_CONFIG_HOME="$TMP/config" XDG_DATA_HOME="$TMP/data" XDG_CACHE_HOME="$TMP/cache"
export XDG_RUNTIME_DIR="$TMP/run"
mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"
export GSETTINGS_BACKEND=memory GDK_BACKEND=x11 GSK_RENDERER=cairo GTK_A11Y=atspi NO_AT_BRIDGE=0
unset WAYLAND_DISPLAY

cleanup() { [ -n "${XVFB:-}" ] && kill "$XVFB" 2>/dev/null; sleep 1; rm -rf "$TMP" 2>/dev/null; }
trap cleanup EXIT

Xvfb :77 -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1 &
XVFB=$!
sleep 0.5
export DISPLAY=:77

dbus-run-session -- bash -c '
  /usr/libexec/at-spi-bus-launcher --launch-immediately >/dev/null 2>&1 &
  sleep 0.5
  timeout 100 python3 "$0"
' "$HERE/probe_env.py"
