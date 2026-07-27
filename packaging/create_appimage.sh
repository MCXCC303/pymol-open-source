#!/bin/bash
# ============================================================================
# PyMOL AppImage Builder
#
# Creates an AppImage from the PyInstaller portable bundle.
#
# Prerequisites:
#   - PyInstaller bundle at dist/PyMOL/
#   - rsvg-convert (from librsvg) or inkscape for icon conversion
#
# Output:
#   dist/PyMOL-<version>-Linux-x86_64.AppImage
#
# Usage:
#   ./packaging/create_appimage.sh
#   PYMOL_VERSION=3.2.0 ./packaging/create_appimage.sh
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJ_ROOT="$(dirname "$SCRIPT_DIR")"
BUNDLE_DIR="${PROJ_ROOT}/dist/PyMOL"
ICON_SVG="${PROJ_ROOT}/data/pymol/icons/icon2.svg"

# -- Configuration -----------------------------------------------------------

PYMOL_VERSION="${PYMOL_VERSION:-3.2.0}"
APPIMAGE_NAME="PyMOL-${PYMOL_VERSION}-Linux-x86_64.AppImage"
APPDIR="${PROJ_ROOT}/dist/PyMOL.AppDir"
ARCH="${ARCH:-x86_64}"

# appimagetool: use system-installed or download
APPIMAGETOOL="${APPIMAGETOOL:-}"
APPIMAGETOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"

echo "============================================"
echo "PyMOL AppImage Builder"
echo "============================================"
echo "  Version:     ${PYMOL_VERSION}"
echo "  Bundle:      ${BUNDLE_DIR}"
echo "  Output:      ${APPIMAGE_NAME}"
echo "============================================"

# -- Check prerequisites -----------------------------------------------------

if [ ! -d "${BUNDLE_DIR}" ]; then
    echo "ERROR: PyInstaller bundle not found at ${BUNDLE_DIR}"
    echo "Run first: python packaging/build_package.py --no-archive"
    exit 1
fi

if [ ! -f "${BUNDLE_DIR}/PyMOL" ]; then
    echo "ERROR: PyMOL executable not found in bundle"
    exit 1
fi

if [ ! -f "${ICON_SVG}" ]; then
    echo "WARNING: Icon SVG not found at ${ICON_SVG}, using placeholder"
    ICON_SVG=""
fi

# -- Clean previous AppDir ---------------------------------------------------

rm -rf "${APPDIR}"
mkdir -p "${APPDIR}"

# -- Copy PyInstaller bundle into AppDir -------------------------------------

echo ""
echo "Copying application bundle into AppDir..."
cp -a "${BUNDLE_DIR}"/* "${APPDIR}/"
cp -a "${BUNDLE_DIR}"/_internal "${APPDIR}/_internal" 2>/dev/null || true

# -- Create AppRun -----------------------------------------------------------

echo "Creating AppRun..."
cat > "${APPDIR}/AppRun" << 'APPRUNEOF'
#!/bin/bash
# AppRun for PyMOL AppImage

SELF="$(readlink -f "$(dirname "$0")")"

# Set library path so bundled Qt/OpenGL libs are found
export LD_LIBRARY_PATH="${SELF}/_internal:${LD_LIBRARY_PATH:-}"

# Ensure PYMOL_PATH is set for data file discovery
# (PyMOL's guess_pymol_path() handles this automatically via the bundled dirs)

# Launch PyMOL, forwarding all arguments
exec "${SELF}/PyMOL" "$@"
APPRUNEOF

chmod +x "${APPDIR}/AppRun"

# -- Create desktop file -----------------------------------------------------

echo "Creating desktop file..."
cat > "${APPDIR}/PyMOL.desktop" << DESKEOF
[Desktop Entry]
Type=Application
Name=PyMOL
GenericName=Molecular Visualization System
Comment=Python-enhanced molecular graphics tool
Exec=AppRun %F
Icon=PyMOL
Categories=Science;Chemistry;Education;
Keywords=molecule;protein;visualization;chemistry;biology;3D;
MimeType=chemical/x-pdb;chemical/x-mdl-molfile;chemical/x-mdl-sdf;
Terminal=false
StartupNotify=true
DESKEOF

# -- Create icon (SVG -> PNG) ------------------------------------------------

echo "Creating icon..."
ICON_PNG="${APPDIR}/PyMOL.png"

if [ -n "${ICON_SVG}" ] && command -v rsvg-convert &>/dev/null; then
    rsvg-convert -w 256 -h 256 "${ICON_SVG}" -o "${ICON_PNG}"
    echo "  Icon converted from SVG (256x256)"
elif [ -n "${ICON_SVG}" ] && command -v inkscape &>/dev/null; then
    inkscape -w 256 -h 256 "${ICON_SVG}" -o "${ICON_PNG}"
    echo "  Icon converted from SVG (256x256)"
else
    # Create a minimal placeholder PNG (1x1 blue pixel)
    # Most desktop environments will use a generic icon
    echo "  WARNING: No SVG converter found (rsvg-convert/inkscape)"
    echo "  Creating placeholder icon..."
    python3 -c "
import struct, zlib
def create_png(path, r, g, b):
    width, height = 256, 256
    raw = b''
    for y in range(height):
        raw += b'\x00' + bytes([r, g, b]) * width
    def chunk(ctype, data):
        c = ctype + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xFFFFFFFF)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(raw)))
        f.write(chunk(b'IEND', b''))
create_png('${ICON_PNG}', 0, 102, 153)
" 2>/dev/null
fi

# -- Create .DirIcon symlink (some FMs use this) -----------------------------

ln -sf PyMOL.png "${APPDIR}/.DirIcon"

# -- Locate or download appimagetool -----------------------------------------

echo ""
echo "Setting up appimagetool..."

if [ -z "${APPIMAGETOOL}" ]; then
    # Check system PATH
    if command -v appimagetool &>/dev/null; then
        APPIMAGETOOL="$(command -v appimagetool)"
    fi
fi

if [ -z "${APPIMAGETOOL}" ]; then
    # Check common locations
    for candidate in \
        /usr/local/bin/appimagetool \
        "${HOME}/.local/bin/appimagetool" \
        "${PROJ_ROOT}/build/appimagetool"; do
        if [ -x "${candidate}" ]; then
            APPIMAGETOOL="${candidate}"
            break
        fi
    done
fi

if [ -z "${APPIMAGETOOL}" ]; then
    echo "  Downloading appimagetool..."
    mkdir -p "${PROJ_ROOT}/build"
    APPIMAGETOOL="${PROJ_ROOT}/build/appimagetool"
    curl -fSL "${APPIMAGETOOL_URL}" -o "${APPIMAGETOOL}"
    chmod +x "${APPIMAGETOOL}"
    echo "  Downloaded to ${APPIMAGETOOL}"
else
    echo "  Using ${APPIMAGETOOL}"
fi

# -- Pre-download runtime file (appimagetool's built-in downloader may fail) --

RUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-${ARCH}"
RUNTIME_FILE="/tmp/runtime-${ARCH}"

if [ ! -f "${RUNTIME_FILE}" ]; then
    echo "Downloading AppImage runtime..."
    if ! curl -fSL --connect-timeout 10 --max-time 60 "${RUNTIME_URL}" -o "${RUNTIME_FILE}" 2>/dev/null; then
        # Fallback: use Python's urllib which handles redirects better
        echo "  curl failed, trying Python urllib..."
        python3 -c "
import urllib.request, shutil, sys
try:
    with urllib.request.urlopen('${RUNTIME_URL}', timeout=60) as r:
        with open('${RUNTIME_FILE}', 'wb') as f:
            shutil.copyfileobj(r, f)
    print('  Downloaded:', __import__('os').path.getsize('${RUNTIME_FILE}'), 'bytes')
except Exception as e:
    print(f'  Failed: {e}', file=sys.stderr)
    sys.exit(1)
" || { echo "  ERROR: Failed to download runtime"; exit 1; }
    fi
fi

RUNTIME_ARG=""
if [ -f "${RUNTIME_FILE}" ] && [ -s "${RUNTIME_FILE}" ]; then
    RUNTIME_ARG="--runtime-file ${RUNTIME_FILE}"
    echo "  Runtime ready: $(du -h ${RUNTIME_FILE} | cut -f1)"
fi

# -- Build AppImage ----------------------------------------------------------

echo ""
echo "Building AppImage..."
echo "  AppDir: ${APPDIR}"
echo "  Output: ${PROJ_ROOT}/dist/${APPIMAGE_NAME}"

# Set ARCH for appimagetool
export ARCH="${ARCH}"

cd "${PROJ_ROOT}/dist"
"${APPIMAGETOOL}" ${RUNTIME_ARG} "${APPDIR}" "${APPIMAGE_NAME}"

# Clean up AppDir (optional - keep for debugging)
# rm -rf "${APPDIR}"

# -- Results -----------------------------------------------------------------

if [ -f "${PROJ_ROOT}/dist/${APPIMAGE_NAME}" ]; then
    SIZE_MB=$(du -m "${PROJ_ROOT}/dist/${APPIMAGE_NAME}" | cut -f1)
    echo ""
    echo "============================================"
    echo "AppImage BUILD SUCCESSFUL"
    echo "============================================"
    echo ""
    echo "  ${PROJ_ROOT}/dist/${APPIMAGE_NAME}"
    echo "  Size: ${SIZE_MB} MB"
    echo ""
    echo "  Test with:"
    echo "    chmod +x dist/${APPIMAGE_NAME}"
    echo "    ./dist/${APPIMAGE_NAME}"
    echo ""
else
    echo "ERROR: AppImage creation failed"
    exit 1
fi
