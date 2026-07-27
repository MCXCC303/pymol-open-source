#!/usr/bin/env python3
"""
PyMOL Open Source - Application Packaging Builder

Builds standalone (portable) PyMOL application bundles for:
  - Windows: PyMOL/ directory with PyMOL.exe
  - macOS:   PyMOL.app bundle
  - Linux:   PyMOL/ directory with PyMOL executable

Prerequisites (in the active Python environment):
  1. PyMOL must be installed and importable:  pip install .
  2. PySide6 must be installed:               pip install PySide6
  3. PyInstaller must be installed:            pip install pyinstaller

Workflow:
  1. Verify environment (all dependencies present)
  2. Run PyInstaller with the spec file
  3. Validate the output bundle
  4. Optionally create platform installer

Usage:
    python packaging/build_package.py              # Build portable bundle
    python packaging/build_package.py --installer  # Also create installer
    python packaging/build_package.py --clean      # Clean build

Environment variables:
    PYMOL_APP_VERSION  - Override version string (default: from PyMOL)
    OUTPUT_DIR         - Output directory (default: dist/)
"""

import argparse
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys


# -- Configuration -----------------------------------------------------------

_PROJ_ROOT = pathlib.Path(__file__).resolve().parent.parent
_PACKAGING_DIR = _PROJ_ROOT / 'packaging'
_DIST_DIR = pathlib.Path(os.environ.get('OUTPUT_DIR', str(_PROJ_ROOT / 'dist')))
_SPEC_FILE = _PACKAGING_DIR / 'pymol.spec'

# Architecture labels for installer filenames
_ARCH = platform.machine().lower()
if _ARCH in ('x86_64', 'amd64'):
    _ARCH_LABEL = 'x86_64'
elif _ARCH in ('arm64', 'aarch64'):
    _ARCH_LABEL = 'arm64'
else:
    _ARCH_LABEL = _ARCH

_OS = sys.platform  # 'win32', 'darwin', 'linux'


# -- Utilities ---------------------------------------------------------------

def run(cmd, **kwargs):
    """Run a command, printing output in real-time."""
    print(f"\n  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=True, **kwargs)


def get_version():
    """Get PyMOL version from the installed package or environment."""
    env_ver = os.environ.get('PYMOL_APP_VERSION', '')
    if env_ver:
        return env_ver

    try:
        import pymol
        # Try pymol._cmd._version or parse from Version.h
        if hasattr(pymol, '__version__'):
            return pymol.__version__
        import pymol._cmd
        return pymol._cmd.get_version()[0]
    except Exception:
        pass

    # Parse from source
    version_h = _PROJ_ROOT / 'layer0' / 'Version.h'
    if version_h.exists():
        match = re.search(r'_PyMOL_VERSION "(.*)"', version_h.read_text())
        if match:
            return match.group(1)

    return '3.2.0'


def verify_environment():
    """Check that all required packages are importable."""
    print("=" * 60)
    print("Verifying build environment...")
    print("=" * 60)

    checks = {
        'pymol': 'pymol',
        'PyMOL C extension': 'pymol._cmd',
        'PySide6 (Qt GUI)': 'PySide6',
        'numpy': 'numpy',
        'PyInstaller': 'PyInstaller',
    }

    all_ok = True
    for label, module_name in checks.items():
        try:
            __import__(module_name)
            print(f"  [OK] {label}")
        except ImportError as e:
            print(f"  [MISSING] {label} — {e}")
            all_ok = False

    if not all_ok:
        print("\nMissing dependencies. Install them with:")
        print("  pip install pymol PySide6 pyinstaller numpy")
        print("\nOr for a fresh build:")
        print("  pip install .[dev]")
        print("  pip install pyinstaller")
        sys.exit(1)

    print()


def build_portable():
    """Run PyInstaller to create the portable application bundle."""
    print("=" * 60)
    print("Building portable application bundle with PyInstaller...")
    print("=" * 60)

    os.chdir(_PROJ_ROOT)

    cmd = [
        sys.executable, '-m', 'PyInstaller',
        '--clean',
        '--noconfirm',
        '--distpath', str(_DIST_DIR),
        '--workpath', str(_PROJ_ROOT / 'build' / 'pyinstaller'),
        str(_SPEC_FILE),
    ]

    run(cmd)

    print(f"\nBuild complete. Output in: {_DIST_DIR}")
    return True


def validate_bundle():
    """Check that the bundled application looks correct."""
    print("\n" + "=" * 60)
    print("Validating application bundle...")
    print("=" * 60)

    if _OS == 'darwin':
        bundle = _DIST_DIR / 'PyMOL.app'
        exe = bundle / 'Contents' / 'MacOS' / 'PyMOL'
    elif _OS == 'win32':
        bundle = _DIST_DIR / 'PyMOL'
        exe = bundle / 'PyMOL.exe'
    else:
        bundle = _DIST_DIR / 'PyMOL'
        exe = bundle / 'PyMOL'

    checks = []

    # Check executable
    if exe.exists():
        checks.append(('Executable', True, str(exe)))
    else:
        checks.append(('Executable', False, f'{exe} not found'))

    # Check data files
    data_found = False
    for root, _dirs, files in os.walk(str(bundle)):
        # Look for shader files which are critical
        if any(f.endswith(('.fs', '.vs', '.gs')) for f in files):
            data_found = True
            break
        # Also check for pymol_path/data
        if 'pymol_path' in root and 'data' in root:
            if files:
                data_found = True
                break

    checks.append(('Data files (shaders etc.)', data_found, ''))

    # Check C extensions
    ext_found = False
    ext_patterns = ['_cmd.*.so', '_cmd.*.pyd', '_cmd.*.dylib']
    for root, _dirs, files in os.walk(str(bundle)):
        for f in files:
            for pat in ext_patterns:
                if re.match(pat.replace('.', r'\.').replace('*', '.*'), f):
                    ext_found = True
                    break

    checks.append(('C extension (_cmd)', ext_found, ''))

    # Check Qt libraries
    qt_found = False
    for root, _dirs, files in os.walk(str(bundle)):
        for f in files:
            if any(name in f for name in ['PySide6', 'Qt6', 'Qt5', 'shiboken6', 'shiboken2']) \
               and any(f.endswith(ext) for ext in ('.so', '.so.6', '.pyd', '.dylib')):
                qt_found = True
                break

    checks.append(('Qt (PySide6) libraries', qt_found, ''))

    for label, ok, detail in checks:
        status = '[OK]' if ok else '[FAIL]'
        d = f' — {detail}' if detail else ''
        print(f"  {status} {label}{d}")

    all_ok = all(ok for _, ok, _ in checks)

    if not all_ok:
        print("\nBundle validation FAILED. Some components are missing.")
        print("Check the PyInstaller output above for warnings.")
        sys.exit(1)

    # Print bundle size
    total_size = 0
    for root, _dirs, files in os.walk(str(bundle)):
        for f in files:
            try:
                total_size += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    size_mb = total_size / (1024 * 1024)
    print(f"\n  Bundle size: {size_mb:.1f} MB")
    print("Validation PASSED.")
    return True


def create_portable_archive():
    """Create a zip/tar archive of the portable bundle."""
    print("\n" + "=" * 60)
    print("Creating portable archive...")
    print("=" * 60)

    version = get_version()

    if _OS == 'darwin':
        bundle_name = 'PyMOL.app'
        archive_name = f'PyMOL-{version}-macOS-{_ARCH_LABEL}'
    elif _OS == 'win32':
        bundle_name = 'PyMOL'
        archive_name = f'PyMOL-{version}-Windows-{_ARCH_LABEL}'
    else:
        bundle_name = 'PyMOL'
        archive_name = f'PyMOL-{version}-Linux-{_ARCH_LABEL}'

    if _OS == 'win32':
        # Create zip on Windows
        archive_path = _DIST_DIR / f'{archive_name}.zip'
        shutil.make_archive(
            str(_DIST_DIR / archive_name),
            'zip',
            root_dir=str(_DIST_DIR),
            base_dir=bundle_name,
        )
    else:
        # Create tar.gz on Unix
        archive_path = _DIST_DIR / f'{archive_name}.tar.gz'
        shutil.make_archive(
            str(_DIST_DIR / archive_name),
            'gztar',
            root_dir=str(_DIST_DIR),
            base_dir=bundle_name,
        )

    size_mb = os.path.getsize(archive_path) / (1024 * 1024)
    print(f"  Archive: {archive_path} ({size_mb:.1f} MB)")
    return archive_path


def create_windows_installer():
    """Create NSIS installer for Windows."""
    if _OS != 'win32':
        print("NSIS installer creation only supported on Windows.")
        return None

    nsis_script = _PACKAGING_DIR / 'installer.nsi'
    if not nsis_script.exists():
        print(f"NSIS script not found: {nsis_script}")
        return None

    print("\n" + "=" * 60)
    print("Creating Windows installer (NSIS)...")
    print("=" * 60)

    version = get_version()

    # Check if makensis is available
    makensis = shutil.which('makensis')
    if not makensis:
        # Try common install locations
        for candidate in [
            r'C:\Program Files (x86)\NSIS\makensis.exe',
            r'C:\Program Files\NSIS\makensis.exe',
        ]:
            if os.path.exists(candidate):
                makensis = candidate
                break

    if not makensis:
        print("  [SKIP] NSIS (makensis) not found. Install NSIS from https://nsis.sourceforge.io/")
        print("  The portable archive can still be used directly (extract and run).")
        return None

    cmd = [
        makensis,
        f'/DPYMOL_VERSION={version}',
        f'/DPYMOL_DIST_DIR={_DIST_DIR / "PyMOL"}',
        f'/DPYMOL_OUTPUT_DIR={_DIST_DIR}',
        str(nsis_script),
    ]

    run(cmd)
    installer_path = _DIST_DIR / f'PyMOL-{version}-Windows-{_ARCH_LABEL}-Setup.exe'
    if installer_path.exists():
        size_mb = os.path.getsize(installer_path) / (1024 * 1024)
        print(f"  Installer: {installer_path} ({size_mb:.1f} MB)")
    return installer_path


def create_macos_dmg():
    """Create a .dmg disk image for macOS."""
    if _OS != 'darwin':
        print("DMG creation only supported on macOS.")
        return None

    print("\n" + "=" * 60)
    print("Creating macOS DMG...")
    print("=" * 60)

    version = get_version()
    app_bundle = _DIST_DIR / 'PyMOL.app'
    dmg_path = _DIST_DIR / f'PyMOL-{version}-macOS-{_ARCH_LABEL}.dmg'
    dmg_temp = _DIST_DIR / 'PyMOL_temp.dmg'

    if not app_bundle.exists():
        print(f"  [FAIL] App bundle not found: {app_bundle}")
        return None

    # Remove existing
    for f in [dmg_path, dmg_temp]:
        if f.exists():
            os.remove(f)

    # Use hdiutil to create DMG
    try:
        # Create temporary DMG
        run([
            'hdiutil', 'create',
            '-srcfolder', str(app_bundle),
            '-volname', f'PyMOL {version}',
            '-fs', 'HFS+',
            '-fsargs', '-c c=64,a=16,e=16',
            '-format', 'UDRW',
            '-size', '2G',
            str(dmg_temp),
        ])

        # Convert to compressed read-only DMG
        run([
            'hdiutil', 'convert',
            str(dmg_temp),
            '-format', 'UDZO',
            '-imagekey', 'zlib-level=9',
            '-o', str(dmg_path),
        ])

        # Clean up
        if dmg_temp.exists():
            os.remove(dmg_temp)

        if dmg_path.exists():
            size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
            print(f"  DMG: {dmg_path} ({size_mb:.1f} MB)")

    except subprocess.CalledProcessError as e:
        print(f"  [FAIL] DMG creation failed: {e}")
        # Simple fallback: create a compressed DMG directly
        try:
            run([
                'hdiutil', 'create',
                '-srcfolder', str(app_bundle),
                '-volname', f'PyMOL {version}',
                '-format', 'UDZO',
                str(dmg_path),
            ])
            if dmg_path.exists():
                size_mb = os.path.getsize(dmg_path) / (1024 * 1024)
                print(f"  DMG (fallback): {dmg_path} ({size_mb:.1f} MB)")
        except subprocess.CalledProcessError:
            return None

    return dmg_path


def create_linux_appimage():
    """Create an AppImage for Linux using the PyInstaller bundle."""
    if _OS not in ('linux', 'linux2'):
        print("AppImage creation only supported on Linux.")
        return None

    print("\n" + "=" * 60)
    print("Creating Linux AppImage...")
    print("=" * 60)

    appimage_script = _PACKAGING_DIR / 'create_appimage.sh'
    if not appimage_script.exists():
        print(f"  [FAIL] AppImage script not found: {appimage_script}")
        return None

    version = get_version()
    appimage_name = f'PyMOL-{version}-Linux-{_ARCH_LABEL}.AppImage'
    appimage_path = _DIST_DIR / appimage_name

    # If AppImage already exists and we're skipping build, return it
    if appimage_path.exists():
        size_mb = os.path.getsize(appimage_path) / (1024 * 1024)
        print(f"  AppImage (existing): {appimage_path} ({size_mb:.1f} MB)")
        return appimage_path

    # Run the AppImage creation script
    env = os.environ.copy()
    env['PYMOL_VERSION'] = version
    env['ARCH'] = _ARCH_LABEL

    try:
        subprocess.run(
            ['bash', str(appimage_script)],
            env=env,
            check=True,
        )
    except subprocess.CalledProcessError:
        print("  [FAIL] AppImage creation failed")
        return None

    if appimage_path.exists():
        size_mb = os.path.getsize(appimage_path) / (1024 * 1024)
        print(f"  AppImage: {appimage_path} ({size_mb:.1f} MB)")
    return appimage_path


def print_summary(archive_path, installer_path):
    """Print build summary."""
    print("\n" + "=" * 60)
    print("BUILD COMPLETE")
    print("=" * 60)

    version = get_version()

    print(f"\n  PyMOL Version: {version}")
    print(f"  Platform:      {_OS} ({_ARCH_LABEL})")

    if _OS == 'darwin':
        print(f"\n  macOS App Bundle:  {_DIST_DIR / 'PyMOL.app'}")
        print(f"    To run: open {_DIST_DIR / 'PyMOL.app'}")
    elif _OS == 'win32':
        print(f"\n  Portable Bundle:   {_DIST_DIR / 'PyMOL'}")
        print(f"    To run: {_DIST_DIR / 'PyMOL' / 'PyMOL.exe'}")
    else:
        print(f"\n  Portable Bundle:   {_DIST_DIR / 'PyMOL'}")
        print(f"    To run: {_DIST_DIR / 'PyMOL' / 'PyMOL'}")

    if archive_path:
        print(f"\n  Portable Archive:  {archive_path}")

    if installer_path:
        print(f"  Installer:         {installer_path}")

    print(f"\n  All artifacts in: {_DIST_DIR}")


# -- Main --------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Build PyMOL standalone application packages'
    )
    parser.add_argument(
        '--installer',
        action='store_true',
        help='Create platform installer (NSIS on Windows, DMG on macOS)'
    )
    parser.add_argument(
        '--archive',
        action='store_true',
        default=True,
        help='Create portable archive (zip/tar.gz)'
    )
    parser.add_argument(
        '--no-archive',
        action='store_false',
        dest='archive',
        help='Skip creating portable archive'
    )
    parser.add_argument(
        '--clean',
        action='store_true',
        help='Clean build directory before building'
    )
    parser.add_argument(
        '--skip-build',
        action='store_true',
        help='Skip PyInstaller build (only archive/installer)'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate an existing bundle'
    )

    args = parser.parse_args()

    if args.validate_only:
        validate_bundle()
        return

    if args.clean:
        _clean_dirs = [
            _PROJ_ROOT / 'build' / 'pyinstaller',
        ]
        for d in _clean_dirs:
            if d.exists():
                shutil.rmtree(d)
                print(f"Cleaned: {d}")

    if not args.skip_build:
        verify_environment()
        build_portable()
        validate_bundle()

    archive_path = None
    if args.archive:
        archive_path = create_portable_archive()

    installer_path = None
    if args.installer:
        if _OS == 'win32':
            installer_path = create_windows_installer()
        elif _OS == 'darwin':
            installer_path = create_macos_dmg()
        else:
            installer_path = create_linux_appimage()

    print_summary(archive_path, installer_path)


if __name__ == '__main__':
    main()
