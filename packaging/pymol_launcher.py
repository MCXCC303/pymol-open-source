"""
PyMOL launcher entry point for PyInstaller-bundled application.

Sets up PYMOL_PATH and Qt environment, then launches PyMOL.
On startup failure, writes diagnostic log to %TEMP%/pymol_startup.log.
"""
import os
import sys
import traceback
from datetime import datetime


def _write_log(msg: str) -> None:
    """Append diagnostic message to the startup log file."""
    try:
        log_dir = os.environ.get('TEMP', os.environ.get('TMP', os.path.dirname(sys.executable)))
        log_path = os.path.join(log_dir, 'pymol_startup.log')
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"[{datetime.now().isoformat()}] {msg}\n")
    except Exception:
        pass  # can't even write log — nothing we can do


def _setup_pymol_path():
    """Configure PYMOL_PATH to find bundled data files."""
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS

        # Data is bundled at pymol/pymol_path/ inside _MEIPASS
        # guess_pymol_path() looks for <pymol_module>/pymol_path first
        pymol_path = os.path.join(bundle_dir, 'pymol', 'pymol_path')

        _write_log(f"Bundle dir: {bundle_dir}")
        _write_log(f"PYMOL_PATH candidate: {pymol_path}")
        _write_log(f"PYMOL_PATH exists: {os.path.isdir(pymol_path)}")

        if os.path.isdir(pymol_path):
            os.environ['PYMOL_PATH'] = pymol_path
            os.environ['PYMOL_DATA'] = os.path.join(pymol_path, 'data')
            os.environ['PYMOL_SCRIPTS'] = os.path.join(pymol_path, 'scripts')
            _write_log("PYMOL_PATH configured OK")
        else:
            _write_log("WARNING: bundled pymol_path not found — will rely on auto-detection")


def _setup_qt_plugins():
    """Ensure Qt finds its platform plugin (qwindows.dll on Windows)."""
    if getattr(sys, 'frozen', False):
        # Qt plugins are at PySide6/plugins/ (conda layout), not PySide6/Qt/plugins/
        qt_plugin_path = os.path.join(sys._MEIPASS, 'PySide6', 'plugins')
        if os.path.isdir(qt_plugin_path):
            os.environ['QT_PLUGIN_PATH'] = qt_plugin_path
            os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(qt_plugin_path, 'platforms')
            _write_log(f"QT_PLUGIN_PATH set to: {qt_plugin_path}")
        else:
            _write_log(f"WARNING: Qt plugin path not found: {qt_plugin_path}")
            alt = os.path.join(sys._MEIPASS, 'PySide6', 'Qt', 'plugins')
            if os.path.isdir(alt):
                os.environ['QT_PLUGIN_PATH'] = alt
                os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = os.path.join(alt, 'platforms')
                _write_log(f"QT_PLUGIN_PATH set to (alt): {alt}")


def main():
    try:
        _write_log("=== PyMOL startup ===")
        _write_log(f"Python: {sys.version}")
        _write_log(f"Executable: {sys.executable}")
        _write_log(f"Frozen: {getattr(sys, 'frozen', False)}")
        _write_log(f"sys.argv: {sys.argv}")

        _setup_pymol_path()
        _setup_qt_plugins()

        _write_log("Importing pymol...")
        import pymol
        _write_log("pymol imported OK")

        _write_log("Calling pymol.launch()...")
        print("""
  =================================================================
   药用人工智能（Pharmaceutical AI）课程教学环境 — PyMOL Open Source
   本版本仅供教育研究用途。商业/监管用途请联系 Schrodinger, Inc.
  =================================================================
""")

        # Verify Qt is importable before handing off to PyMOL.
        # If Qt fails, PyMOL silently falls back to GLUT (which is
        # not compiled in) and crashes with a misleading
        # "NotImplementedError: compile with --glut".
        try:
            __import__('pmg_qt.pymol_qt_gui')
            _write_log("pmg_qt import OK")
        except ImportError as e:
            _write_log(f"FATAL: cannot import pmg_qt: {e}")
            # Try to diagnose: list files in PySide6 package
            pyside_dir = os.path.join(sys._MEIPASS, 'PySide6')
            if os.path.isdir(pyside_dir):
                _write_log(f"PySide6 contents: {os.listdir(pyside_dir)[:20]}")
            raise RuntimeError(
                f"无法加载 Qt 图形界面 ({e})\n\n"
                f"请检查显卡驱动或尝试：\n"
                f"  set QT_OPENGL=software\n"
                f"  PyMOL.exe"
            ) from e

        pymol.launch()

    except SystemExit:
        _write_log("PyMOL exited normally (SystemExit)")
        raise
    except Exception:
        _write_log(f"FATAL: {traceback.format_exc()}")
        # On Windows with runw bootloader, errors are invisible.
        # Try to show a message box if we can.
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"PyMOL failed to start:\n\n{traceback.format_exc()}",
                "PyMOL Startup Error",
                0x10,  # MB_ICONERROR
            )
        except Exception:
            pass
        raise


if __name__ == '__main__':
    main()
