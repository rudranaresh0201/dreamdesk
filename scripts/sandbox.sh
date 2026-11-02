#!/usr/bin/env bash
# Runs a command with no access to your real files, drives, network, desktop or user services.
# It starts from an empty filesystem: only what's listed here exists inside. Each run gets its
# own display, D-Bus and HOME, all deleted when it ends.
#
#   scripts/sandbox.sh [--out DIR] COMMAND...
#
# --out DIR is the only real folder the command can write to. tests/check_sandbox.py proves this.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT=""
if [ "${1:-}" = "--out" ]; then
  OUT="$(realpath -m "$2")"
  mkdir -p "$OUT"
  shift 2
fi

ARGS=(
  --die-with-parent --new-session --unshare-all --cap-drop ALL --clearenv
  --ro-bind /usr /usr
  --symlink usr/bin /bin --symlink usr/sbin /sbin --symlink usr/lib /lib --symlink usr/lib64 /lib64
  --proc /proc --dev /dev --tmpfs /tmp --tmpfs /run --tmpfs /var
)
for path in /etc/fonts /etc/ld.so.cache /etc/alternatives /etc/localtime /etc/nsswitch.conf /etc/passwd /etc/group /etc/dbus-1 /etc/xdg; do
  ARGS+=(--ro-bind-try "$path" "$path")
done
# App installs that live outside /usr, read-only.
for path in /opt/libreoffice26.8 /opt/google/chrome; do
  ARGS+=(--ro-bind-try "$path" "$path")
done
# Code only, read-only, at a neutral path so your home folder doesn't exist inside.
# data/, runs/ and .git stay out so an agent can't reach them.
WORK=/work/dreamdesk
for path in dreamdesk scripts tests .venv; do
  ARGS+=(--ro-bind-try "$ROOT/$path" "$WORK/$path")
done
[ -n "$OUT" ] && ARGS+=(--bind "$OUT" "$OUT")
ARGS+=(
  --chdir "$WORK"
  --setenv PATH /usr/local/bin:/usr/bin --setenv LANG C.UTF-8
  --setenv XDG_SESSION_TYPE x11  # otherwise Chrome and VS Code pick Wayland by themselves
  --setenv GTK_USE_PORTAL 0 --setenv ADW_DISABLE_PORTAL 1  # keep file dialogs on the private display
)
# The display number is private to this sandbox, so parallel runs can all use the same one.
# A fake machine ID: some apps need one, and this hides the real one.
exec bwrap "${ARGS[@]}" --ro-bind-data 3 /etc/machine-id bash scripts/private.sh 90 "$@" 3<<< "00000000000000000000000000d12ea3"
