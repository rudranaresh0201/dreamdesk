#!/usr/bin/env bash
# Runs a command inside a private, invisible desktop: its own display, D-Bus and
# accessibility buses, HOME and in-memory settings. Your real desktop is never touched.
# Same idea as the `xs` script from the habit experiments.
#
#   scripts/private.sh DISPLAY_NUMBER COMMAND...
set -u
N="$1"; shift
TMP="$(mktemp -d)"
export HOME="$TMP" XDG_CONFIG_HOME="$TMP/config" XDG_DATA_HOME="$TMP/data" XDG_CACHE_HOME="$TMP/cache"
export XDG_RUNTIME_DIR="$TMP/run" GSETTINGS_BACKEND=memory GDK_BACKEND=x11 GSK_RENDERER=cairo
export GTK_A11Y=atspi NO_AT_BRIDGE=0 DISPLAY=":$N"
unset WAYLAND_DISPLAY
mkdir -p "$XDG_RUNTIME_DIR" && chmod 700 "$XDG_RUNTIME_DIR"

cleanup() { [ -n "${XVFB:-}" ] && kill "$XVFB" 2>/dev/null; sleep 1; rm -rf "$TMP" 2>/dev/null; }
trap cleanup EXIT

Xvfb ":$N" -screen 0 1280x800x24 -nolisten tcp >/dev/null 2>&1 &
XVFB=$!
for _ in $(seq 50); do [ -e "/tmp/.X11-unix/X$N" ] && break; sleep 0.1; done

dbus-run-session -- bash -c '/usr/libexec/at-spi-bus-launcher --launch-immediately >/dev/null 2>&1 & sleep 0.5; exec "$@"' _ "$@" 2>/dev/null
