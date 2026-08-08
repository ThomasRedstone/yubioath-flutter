#!/bin/sh
# Click apps aren't guaranteed a particular cwd, so resolve paths relative
# to this script's own location — the same install directory the rest of
# the package's files land in.
DIR="$(cd "$(dirname "$0")" && pwd)"

# Real UT app launches (via ubuntu-app-launch/upstart) get their Wayland
# target as MIR_SERVER_WAYLAND_HOST, a single "<dir>/<socket-name>" path,
# not separate XDG_RUNTIME_DIR/WAYLAND_DISPLAY vars — split it back into
# the two vars wayland-client actually looks for. See ~/own/ut/ut-flutter-embedder.md.
if [ -n "$MIR_SERVER_WAYLAND_HOST" ]; then
    export XDG_RUNTIME_DIR="$(dirname "$MIR_SERVER_WAYLAND_HOST")"
    export WAYLAND_DISPLAY="$(basename "$MIR_SERVER_WAYLAND_HOST")"
fi
echo "[run.sh] MIR_SOCKET=$MIR_SOCKET MIR_SERVER_WAYLAND_HOST=$MIR_SERVER_WAYLAND_HOST XDG_RUNTIME_DIR=$XDG_RUNTIME_DIR WAYLAND_DISPLAY=$WAYLAND_DISPLAY" >&2

# Unlike the x64 build (cross-glibc mismatch against the old VM), this
# binary and libflutter_engine.so were built for the device's own arm64
# glibc 2.39 — no bundled ld.so/foreign-linker trick needed, just point
# LD_LIBRARY_PATH at the payload dir (and native_assets, for sqflite_common_ffi
# style plugins that dlopen a bundled .so) and exec directly.
export LD_LIBRARY_PATH="$DIR:$DIR/flutter_assets/native_assets/linux:$LD_LIBRARY_PATH"

exec "$DIR/flutter-ut-embedder" --assets "$DIR/flutter_assets" --icu "$DIR/icudtl.dat"
