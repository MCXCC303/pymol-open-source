# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for PyMOL Open Source

Produces a standalone (onedir) bundle with:
  - Python interpreter
  - PyMOL C extensions (_cmd, _champ)
  - Qt GUI (PySide6)
  - All data files (shaders, icons, demo, etc.)
  - System libraries (OpenGL, GLEW, freetype, libpng)

Usage:
    pyinstaller --clean --noconfirm packaging/pymol.spec
"""

import importlib.util
import os
import pathlib
import sys
import sysconfig
import site

# -- Project root discovery --------------------------------------------------

_PROJ_ROOT = pathlib.Path(SPECPATH).parent  # packaging/.. -> project root
_PACKAGING_DIR = pathlib.Path(SPECPATH)     # packaging/

# -- PyMOL discovery ---------------------------------------------------------

def _find_pymol_module():
    """Find the pymol Python package directory."""
    # Try importlib first
    try:
        spec = importlib.util.find_spec('pymol')
        if spec and spec.origin:
            pymol_init = pathlib.Path(spec.origin)
            if pymol_init.exists():
                return pymol_init.parent
    except (ImportError, ValueError):
        pass

    # Fall back to searching site-packages
    for sp in site.getsitepackages():
        candidate = pathlib.Path(sp) / 'pymol' / '__init__.py'
        if candidate.exists():
            return candidate.parent

    # Fall back to the modules/ directory in the project
    candidate = _PROJ_ROOT / 'modules' / 'pymol'
    if candidate.exists():
        return candidate

    raise RuntimeError("Cannot find pymol package. Install PyMOL first with: pip install .")


_PYMOL_DIR = _find_pymol_module()
print(f"PyMOL package found at: {_PYMOL_DIR}")

# -- Data files --------------------------------------------------------------

# Determine PYMOL_PATH for data files
_data_src = _PROJ_ROOT / 'data'
if not _data_src.exists():
    # Try the installed location
    _data_src = _PYMOL_DIR / 'pymol_path' / 'data'
    if not _data_src.exists():
        _data_src = pathlib.Path(sys.prefix) / 'share' / 'pymol' / 'data'

_data_dst = os.path.join('pymol', 'pymol_path', 'data')

print(f"Data source: {_data_src}")
print(f"Data dest:   {_data_dst}")

added_files = [
    (_data_src, _data_dst),
]

# Also add examples and test directories if building from source
for _extra_dir in ['examples', 'test']:
    _extra_src = _PROJ_ROOT / _extra_dir
    if _extra_src.exists():
        added_files.append((_extra_src, os.path.join('pymol', 'pymol_path', _extra_dir)))

# Add LICENSE
_license_src = _PROJ_ROOT / 'LICENSE'
if _license_src.exists():
    added_files.append((_license_src, 'pymol/pymol_path'))

# -- Hidden imports ----------------------------------------------------------

def _collect_submodules(package_names):
    """Discover all submodules of a package to catch dynamic imports."""
    result = []
    for pkg_name in package_names:
        result.append(pkg_name)
        try:
            spec = importlib.util.find_spec(pkg_name)
            if spec and spec.origin:
                pkg_dir = pathlib.Path(spec.origin).parent
                for py_file in sorted(pkg_dir.rglob('*.py')):
                    # Convert path to dotted module name
                    rel = py_file.relative_to(pkg_dir.parent)
                    parts = list(rel.parts)
                    parts[-1] = parts[-1].replace('.py', '')
                    if parts[-1] == '__init__':
                        parts = parts[:-1]
                    if parts:
                        mod_name = '.'.join(parts)
                        if mod_name not in result:
                            result.append(mod_name)
        except (ImportError, ValueError, AttributeError):
            pass
    return result

hiddenimports = _collect_submodules([
    'pymol',
    'pymol2',
    'chempy',
    'chempy.champ',
    'pmg_qt',
    'pmg_tk',
])

hiddenimports += [
    # Data formats / extras (not auto-discovered)
    'msgpack',
    'PIL',
    'PIL.Image',
    # Standard lib extras that may be missed
    'xml.etree.ElementTree',
    'lzma',
    'bz2',
    'sqlite3',
    'ctypes',
]

# Platform-specific
if sys.platform == 'win32':
    hiddenimports += [
        'win32api',
        'win32con',
        'win32gui',
    ]

# -- Binaries ----------------------------------------------------------------

binaries = []

# Collect shared libraries that PyInstaller might miss
def _collect_libs_from_packages(package_names):
    """Find .so/.pyd/.dylib/.dll files in the given packages."""
    result = []
    for pkg_name in package_names:
        try:
            spec = importlib.util.find_spec(pkg_name)
            if spec and spec.origin:
                pkg_dir = pathlib.Path(spec.origin).parent
                for pattern in ['*.so', '*.pyd', '*.dylib', '*.dll']:
                    for f in pkg_dir.rglob(pattern):
                        # Use the file's parent dir as destination
                        rel_path = f.relative_to(pkg_dir.parent)
                        result.append((str(f), str(rel_path.parent)))
        except (ImportError, ValueError, AttributeError):
            pass
    return result

binaries += _collect_libs_from_packages(['pymol', 'chempy.champ'])

# -- Collect OpenGL fallback DLLs for Windows ---------------------------------

if sys.platform == 'win32':
    # Mesa software OpenGL renderer and ANGLE (Direct3D translation layer)
    # Needed when the system lacks a desktop OpenGL driver (VM, remote desktop)
    _ogl_dlls = ['opengl32sw.dll', 'libEGL.dll', 'libGLESv2.dll', 'd3dcompiler_47.dll']
    for _dll_name in _ogl_dlls:
        for _prefix in prefix_path:
            _candidate = os.path.join(_prefix, 'Library', 'bin', _dll_name)
            if os.path.exists(_candidate):
                binaries.append((_candidate, '.'))
                print(f"Added OpenGL fallback: {_candidate}")
                break

# -- Excludes ----------------------------------------------------------------

excludes = [
    'tkinter',
    'Tkinter',
    'matplotlib',
    'scipy',
    'pandas',
    'IPython',
    'jupyter',
    'notebook',
]

# -- PyInstaller Analysis ----------------------------------------------------

a = Analysis(
    [str(_PACKAGING_DIR / 'pymol_launcher.py')],
    pathex=[str(_PROJ_ROOT), str(_PYMOL_DIR.parent), str(_PYMOL_DIR)],
    binaries=binaries,
    datas=added_files,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)

# -- Platform-specific EXE settings ------------------------------------------

_exe_name = 'PyMOL'

if sys.platform == 'darwin':
    # macOS .app bundle: EXE → COLLECT → BUNDLE
    pyz = PYZ(a.pure)
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=_exe_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=False,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=_exe_name,
    )
    app = BUNDLE(
        coll,
        name=f'{_exe_name}.app',
        icon=None,
        bundle_identifier='org.pymol.pymol',
        info_plist={
            'NSPrincipalClass': 'NSApplication',
            'NSHighResolutionCapable': 'True',
            'CFBundleName': 'PyMOL',
            'CFBundleDisplayName': 'PyMOL Molecular Graphics System',
            'CFBundleGetInfoString': 'PyMOL - Molecular Visualization',
            'CFBundleShortVersionString': '3.2.0',
            'CFBundleVersion': '3.2.0.0',
            'CFBundleIdentifier': 'org.pymol.pymol',
            'NSHumanReadableCopyright': 'Copyright (c) Schrodinger, LLC',
            'LSRequiresNativeExecution': True,
            'NSRequiresAquaSystemAppearance': 'False',
            'LSEnvironment': {
                'PYMOL_DATA': os.path.join('pymol', 'pymol_path', 'data'),
            },
        },
    )

else:
    # Windows / Linux onedir
    pyz = PYZ(a.pure)

    # Use console=True on Windows for debugging (shows stdout/stderr)
    # Change to console=False for release builds
    _win_console = os.environ.get('PYMOL_CONSOLE', '1' if sys.platform == 'win32' else '0') == '1'

    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name=f'{_exe_name}.exe' if sys.platform == 'win32' else _exe_name,
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        console=_win_console,
        icon=None,
    )

    coll = COLLECT(
        exe,
        a.binaries,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=[],
        name=_exe_name,
    )
