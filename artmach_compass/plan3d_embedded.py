"""Expose the bundled Plan3D drawing renderer inside Compass."""

from artmach_compass.plan3d_backend import create_cad_viewport


def create_embedded_plan3d_viewport(parent):
    return create_cad_viewport(parent)
