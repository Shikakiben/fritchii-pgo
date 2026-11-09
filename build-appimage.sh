#!/bin/bash
# Packs NX2navi's Linux build kit plus this GUI into one AppImage.
#
#   ./build-appimage.sh <path to an NX2navi source checkout at the tag you want>
#
# What it does:
#   1. copies what tools/make_appimage.py copies (recomp, runtime, tools, bin/nx2navi_xlate,
#      toolchain/vma) and ADDS the GUI;
#   2. fetches a relocatable CPython 3.14 (python-build-standalone, the one `uv python install 3.14`
#      puts in ~/.local/share/uv/python) with numpy, lz4, zstandard;
#   3. writes an AppRun that starts the window;
#   4. packs it with appimagetool.
#
# The result builds the game on the player's PC from their own .nup; it contains no game files.
set -euo pipefail

KIT_SRC=${1:?usage: build-appimage.sh <NX2navi source checkout>}
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT=${OUT:-$HERE/dist}
APP=$HERE/AppDir
CACHE=${CACHE:-$HERE/.cache}
PY_URL=${PY_URL:-https://github.com/astral-sh/python-build-standalone/releases/download/20261026/cpython-3.14.10+20261026-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz}
AIT_URL=${AIT_URL:-https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage}
RT_URL=${RT_URL:-https://github.com/AppImage/type2-runtime/releases/download/20251108/runtime-x86_64}

say() { printf '\033[1m[nx2gui]\033[0m %s\n' "$*"; }
fetch() { [ -s "$2" ] || { say "fetching $(basename "$2")"; curl -fL --retry 5 --retry-all-errors -o "$2.part" "$1"; mv "$2.part" "$2"; }; }

# ---- checks on the source checkout
test -f "$KIT_SRC/tools/make_game.py" || { echo "not an NX2navi checkout: $KIT_SRC" >&2; exit 1; }
test -f "$KIT_SRC/build/xlate/nx2navi_xlate" || {
    echo "the shader translator is not built: run  python3 tools/build_xlate.py  in $KIT_SRC" >&2; exit 1; }
VERSION=$(cat "$KIT_SRC/VERSION" 2>/dev/null || echo unknown)

mkdir -p "$CACHE" "$OUT"
fetch "$PY_URL" "$CACHE/python.tar.gz"
fetch "$AIT_URL" "$CACHE/appimagetool.AppImage"
fetch "$RT_URL" "$CACHE/runtime-x86_64"
chmod +x "$CACHE/appimagetool.AppImage"

say "assembling AppDir ($VERSION)"
rm -rf "$APP"
KIT=$APP/usr/kit
mkdir -p "$KIT" "$APP/usr/bin" "$APP/usr/python"

# ---- what tools/make_appimage.py copies, unchanged
for d in recomp runtime; do cp -a "$KIT_SRC/$d" "$KIT/$d"; done
mkdir -p "$KIT/tools"
(cd "$KIT_SRC/tools" && tar -cf - --exclude=vendor --exclude=xlate --exclude=__pycache__ .) \
    | (cd "$KIT/tools" && tar -xf -)
for f in VERSION LICENSE LICENSE-ADDITIONS THIRD_PARTY_NOTICES.md nx2navi.ini.example; do
    [ -f "$KIT_SRC/$f" ] && cp -a "$KIT_SRC/$f" "$KIT/$f"
done
mkdir -p "$KIT/docs" "$KIT/bin" "$KIT/toolchain/vma"
cp -a "$KIT_SRC/docs/README-BuildKit.md" "$KIT/docs/" 2>/dev/null || true
cp -a "$KIT_SRC/build/xlate/nx2navi_xlate" "$KIT_SRC/build/xlate/nx2navi_xlate.id" "$KIT/bin/"
cp -a "$KIT_SRC/toolchain/vma/vk_mem_alloc.h" "$KIT/toolchain/vma/" 2>/dev/null \
    || say "note: VMA header not present, build_game.py will fetch it on first use"

# ---- the GUI (this repository)
say "adding the window"
mkdir -p "$APP/usr/share/nx2navi-gui"
cp -a "$HERE/usr/share/nx2navi-gui/gui.py" "$APP/usr/share/nx2navi-gui/gui.py"

# ---- relocatable CPython with the kit's packages
say "unpacking Python"
tar -xzf "$CACHE/python.tar.gz" -C "$APP/usr" --strip-components=1
find "$APP/usr/python" -name EXTERNALLY-MANAGED -delete 2>/dev/null || true
"$APP/usr/python/bin/python3" -m pip install --quiet --disable-pip-version-check \
    --no-warn-script-location numpy lz4 zstandard pillow
find "$APP/usr/python" -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true

# ---- the entry point
cat > "$APP/AppRun" <<'APPRUN'
#!/bin/sh
# NX2navi (Linux, GUI): builds Ocarina of Time (Switch 2) from your own .nup dump.
HERE="$(dirname "$(readlink -f "$0")")"
export NX2NAVI_KIT="$HERE/usr/kit"
export NX2NAVI_PY="$HERE/usr/python/bin/python3"
export NX2NAVI_GUI="$HERE/usr/share/nx2navi-gui"
unset PYTHONPATH PYTHONHOME
exec "$NX2NAVI_PY" -I "$NX2NAVI_GUI/gui.py" "$@"
APPRUN
chmod +x "$APP/AppRun"

cat > "$APP/nx2navi.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=NX2navi (build Ocarina of Time)
Comment=Build Ocarina of Time (Switch 2) natively from your own .nup dump
Exec=AppRun
Icon=nx2navi
Terminal=false
Categories=Game;
DESKTOP

ICON=$KIT_SRC/runtime/nx2navi.ico
if [ -f "$ICON" ]; then
    "$APP/usr/python/bin/python3" - "$ICON" "$APP/nx2navi.png" <<'PY'
import sys
from PIL import Image
src, dst = sys.argv[1], sys.argv[2]
with Image.open(src) as ico:
    ico.size = max(ico.ico.sizes())
    ico.convert("RGBA").save(dst)
PY
fi

# ---- pack
say "packing"
TARGET=$OUT/NX2navi-Linux-GUI-$VERSION-x86_64.AppImage
ARCH=x86_64 "$CACHE/appimagetool.AppImage" --no-appstream --runtime-file "$CACHE/runtime-x86_64" \
    "$APP" "$TARGET"
chmod +x "$TARGET"
sha256sum "$TARGET" > "$TARGET.sha256"
say "done: $TARGET ($(du -h "$TARGET" | cut -f1))"
