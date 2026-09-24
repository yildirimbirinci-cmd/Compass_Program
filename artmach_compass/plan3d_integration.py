"""Embed the existing Plan3D Qt window inside the Compass workspace.

The initial integration uses the user's checked-out Plan3D source. Set
ARTMACH_COMPASS_PLAN3D_PATH if the checkout is outside Desktop/Plan3D.
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QMainWindow


def create_plan3d_window() -> QMainWindow:
    root = Path(
        os.environ.get("ARTMACH_COMPASS_PLAN3D_PATH")
        or Path.home() / "Desktop" / "Plan3D"
    ).expanduser().resolve()
    entry = root / "src" / "app" / "main.py"
    if not entry.is_file():
        raise RuntimeError(
            f"Plan3D source was not found at {entry}. "
            "Set ARTMACH_COMPASS_PLAN3D_PATH to your Plan3D checkout."
        )

    # Plan3D's confirmed runtime imports its app modules by short names and
    # its CAD modules through src.cad. Importing the module installs its
    # project, theme, export and cursor runtimes without starting a second
    # QApplication or event loop.
    for directory in (root, root / "src" / "app"):
        location = str(directory)
        if location not in sys.path:
            sys.path.insert(0, location)
    module = importlib.import_module("src.app.main")
    window = module.MainWindow()
    window.setWindowTitle("Plan3D")
    return window
