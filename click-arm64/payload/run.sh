#!/bin/sh
# Self-contained app runtime; no dependency on another click's install path.
set -eu
DIR="${APP_DIR:-${0%/*}}"
[ "$DIR" != "$0" ] || DIR="$PWD"
# Runtime and assets stay absolute after the launcher changes its working directory.
case "$DIR" in /*) ;; *) DIR="$PWD/$DIR" ;; esac
DIR=$(CDPATH= cd "$DIR" && pwd -P)
RUNTIME="$DIR/runtime"
python3 "$DIR/preflight.py" "$RUNTIME"
if [ -n "${MIR_SERVER_WAYLAND_HOST:-}" ]; then
    export XDG_RUNTIME_DIR="${MIR_SERVER_WAYLAND_HOST%/*}"
    export WAYLAND_DISPLAY="${MIR_SERVER_WAYLAND_HOST##*/}"
fi
APP_PACKAGE=yubioath-flutter.thomasredstone
export XDG_DATA_HOME="$HOME/.local/share/$APP_PACKAGE"
export XDG_CONFIG_HOME="$HOME/.config/$APP_PACKAGE"
export XDG_CACHE_HOME="$HOME/.cache/$APP_PACKAGE"
mkdir -p "$XDG_CACHE_HOME/cwd"
cd "$XDG_CACHE_HOME/cwd"
export LD_LIBRARY_PATH="$RUNTIME:$DIR/flutter_assets/native_assets/linux:${LD_LIBRARY_PATH:-}"
export _HELPER_PATH="${YUBIOATH_HELPER_PATH:-$HOME/.local/share/yubioath-helper/authenticator-helper}"
[ -x "$_HELPER_PATH" ] || { echo "Install the reviewed ARM64 CPython3.12 helper and pcscd first" >&2; exit 1; }
exec "$RUNTIME/flutter-ut-embedder" --app-id "$APP_PACKAGE" --assets "$DIR/flutter_assets" --icu "$RUNTIME/icudtl.dat"
