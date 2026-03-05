"""
launch_gui.py
=============
Convenience launcher for the DWSIM Gasification Model GUI.

Run from the project root:
    python launch_gui.py

This is equivalent to:
    python -m dwsim_model.gui
"""

import sys
from pathlib import Path

# Ensure the src/ directory is on the Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dwsim_model.gui.main_window import launch

if __name__ == "__main__":
    launch()
