#!/bin/sh
# Click apps aren't guaranteed a particular cwd, so resolve paths relative
# to this script's own location — the same install directory the rest of
# this app's own files (flutter_assets/) land in.
DIR="$(cd "$(dirname "$0")" && pwd)"

# 2026-08-08: the embedder binary + libflutter_engine.so + icudtl.dat
# used to be bundled into every single app's own click (~180MB each,
# ~4 copies). That's what let a real bug through: the on-screen-
# keyboard fix landed in the embedder, got redeployed to two of four
# apps, and the other two silently kept running the old broken copy
# with no indication anything was stale. Now every app references one
# shared "runtime" click's stable install path instead — updating the
# runtime updates every app that uses it, in one push. See
# ~/own/ut/ut-flutter-embedder.md for the full story.
RUNTIME="/opt/click.ubuntu.com/flutter-ut-embedder-runtime.thomasredstone/current"

# Real UT app launches (via ubuntu-app-launch/upstart) get their Wayland
# target as MIR_SERVER_WAYLAND_HOST, a single "<dir>/<socket-name>" path,
# not separate XDG_RUNTIME_DIR/WAYLAND_DISPLAY vars — split it back into
# the two vars wayland-client actually looks for.
if [ -n "$MIR_SERVER_WAYLAND_HOST" ]; then
    export XDG_RUNTIME_DIR="$(dirname "$MIR_SERVER_WAYLAND_HOST")"
    export WAYLAND_DISPLAY="$(basename "$MIR_SERVER_WAYLAND_HOST")"
fi

# 2026-08-08: click apps aren't launched with any particular cwd either
# (and the install dir under /opt/click.ubuntu.com/ is read-only
# anyway) — several plugins default to *relative* paths assuming a
# writable cwd (found via OpenHIIT's `background_hiit_timer` plugin:
# `sqflite_common_ffi`'s own default database path is the literal
# relative path `.dart_tool/sqflite_common_ffi/databases`, which
# doesn't exist and couldn't be created even if sqlite tried — it
# doesn't auto-create missing parent directories, hence
# SQLITE_CANTOPEN/"unable to open database file"). Give every app a
# real, writable, guaranteed-to-exist cwd instead of leaving it to
# chance — mirrors the install path under a writable cache root so
# it's unique per app with no parsing needed.
CWD_DIR="$HOME/.cache/flutter-ut-embedder-cwd$DIR"
mkdir -p "$CWD_DIR"
cd "$CWD_DIR" || true

echo "[run.sh] MIR_SOCKET=$MIR_SOCKET MIR_SERVER_WAYLAND_HOST=$MIR_SERVER_WAYLAND_HOST XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY RUNTIME=$RUNTIME CWD=$(pwd)" >&2

# libflutter_engine.so comes from the shared runtime click; native_assets
# (e.g. sqflite_common_ffi's bundled libsqlite3.so) stays with THIS app,
# since it's this app's own Flutter build that generated it.
export LD_LIBRARY_PATH="$RUNTIME:$DIR/flutter_assets/native_assets/linux:$LD_LIBRARY_PATH"

# 2026-08-09: upstream ships a PyInstaller-bundled authenticator-helper
# binary for x86_64/macOS/Windows, but PyInstaller can't cross-compile
# (must run natively on the target arch), and this UT image's apt
# index has no build-essential/python3-dev/swig to build one on-device
# either. lib/desktop/init.dart honors this _HELPER_PATH override
# instead: points straight at the real on-device CPython 3.12, with
# every dependency (including pyscard's _scard extension, cross-
# compiled for aarch64 -- no Linux wheels exist on PyPI at all) vendored
# into a flat PYTHONPATH tree. See ~/own/ut/ut-flutter-embedder.md
# (item 4) for the full story, including the pcscd/libccid payload
# this also needed (absent from this image's apt index too).
export _HELPER_PATH="/home/phablet/.local/share/yubioath-helper/authenticator-helper"

exec "$RUNTIME/flutter-ut-embedder" --assets "$DIR/flutter_assets" --icu "$RUNTIME/icudtl.dat"
