"""
PyMOL launcher entry point for PyInstaller-bundled application.

Sets up PYMOL_PATH to point to bundled data files, then launches PyMOL.
"""
import os
import sys

# -- Locate bundled data -----------------------------------------------------

def _setup_pymol_path():
    """Configure PYMOL_PATH to find bundled data files."""

    # In a PyInstaller bundle, sys._MEIPASS is the _internal/ directory
    # where all Python packages and data files are stored
    if getattr(sys, 'frozen', False):
        bundle_dir = sys._MEIPASS

        # Data is bundled at pymol/pymol_path/ inside _MEIPASS
        # guess_pymol_path() looks for <pymol_module>/pymol_path first
        pymol_path = os.path.join(bundle_dir, 'pymol', 'pymol_path')

        if os.path.isdir(pymol_path):
            os.environ['PYMOL_PATH'] = pymol_path
            os.environ['PYMOL_DATA'] = os.path.join(pymol_path, 'data')
            os.environ['PYMOL_SCRIPTS'] = os.path.join(pymol_path, 'scripts')
            return

    # Not bundled or data not found — let PyMOL's default discovery handle it
    pass


# -- Main --------------------------------------------------------------------

def main():
    _setup_pymol_path()

    # Import and launch PyMOL
    import pymol

    # Forward command-line arguments
    pymol.launch()


if __name__ == '__main__':
    main()
