"""Button-free integration of the Plan3D engine into Compass.

The source engine lives beside this adapter in ``artmach_compass/plan3d_engine``.
UI actions can call these methods later without embedding the Plan3D main window
or introducing controls into Compass.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


def _activate_engine():
    root = Path(__file__).resolve().parent / "plan3d_engine"
    if not (root / "src" / "cad" / "viewport.py").is_file():
        raise RuntimeError("The integrated Plan3D engine is missing")
    # The upstream engine uses both `src.cad` and short `app`-module imports.
    # Keep its import root isolated until a Plan3D operation is requested.
    for path in (root, root / "src" / "app"):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def create_cad_viewport(*args, **kwargs):
    """Create the native drawing view for Compass's Drawing Area."""
    _activate_engine()
    return importlib.import_module("src.cad.viewport").CadViewport(*args, **kwargs)


def analyze_facade_windows(viewport, facade_rects, floor_settings, *, measurement_layer="C Ölçü"):
    """Compute all confirmed floors using a separate datum for each facade."""
    _activate_engine()
    from artmach_compass.plan3d_engine.window_heights import analyze_window_heights
    return analyze_window_heights(viewport, facade_rects, floor_settings,
                                  measurement_layer=measurement_layer)


def configure_exterior_door_layers(viewport, layer_names):
    """Store this project's exterior-door source layers on its own viewport."""
    names = tuple(str(name).strip() for name in layer_names if str(name).strip())
    if not names:
        raise ValueError("At least one exterior-door layer is required")
    viewport._exterior_door_layers = names


def prepare_max_transfer(export_panel):
    """Prepare the existing Plan3D MaxScript bridge from an assigned project.

    The caller must supply the engine's ExportDetailsPanel with confirmed
    plan/facade assignments and pivots. This function does not execute Max.
    """
    _activate_engine()
    bridge = importlib.import_module("plan3d_max_bridge")
    return bridge.prepare_wall_only_transfer(export_panel)
