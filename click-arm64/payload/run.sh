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
RUNTIME="/opt/click.ubuntu.com/flutter-ut-embedder-runtime.tom/current"

# Real UT app launches (via ubuntu-app-launch/upstart) get their Wayland
# target as MIR_SERVER_WAYLAND_HOST, a single "<dir>/<socket-name>" path,
# not separate XDG_RUNTIME_DIR/WAYLAND_DISPLAY vars — split it back into
# the two vars wayland-client actually looks for.
if [ -n "$MIR_SERVER_WAYLAND_HOST" ]; then
    export XDG_RUNTIME_DIR="$(dirname "$MIR_SERVER_WAYLAND_HOST")"
    export WAYLAND_DISPLAY="$(basename "$MIR_SERVER_WAYLAND_HOST")"
fi
echo "[run.sh] MIR_SOCKET=$MIR_SOCKET MIR_SERVER_WAYLAND_HOST=$MIR_SERVER_WAYLAND_HOST XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY RUNTIME=$RUNTIME" >&2

# libflutter_engine.so comes from the shared runtime click; native_assets
# (e.g. sqflite_common_ffi's bundled libsqlite3.so) stays with THIS app,
# since it's this app's own Flutter build that generated it.
export LD_LIBRARY_PATH="$RUNTIME:$DIR/flutter_assets/native_assets/linux:$LD_LIBRARY_PATH"

exec "$RUNTIME/flutter-ut-embedder" --assets "$DIR/flutter_assets" --icu "$RUNTIME/icudtl.dat"
