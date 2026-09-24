from __future__ import annotations

import math
import random

from PySide6.QtGui import QImage


_TILE_SIZE = 64
_rng = random.Random(0xA17C0A55)
_threshold_values = list(range(_TILE_SIZE * _TILE_SIZE))
_rng.shuffle(_threshold_values)
_DITHER_THRESHOLDS = tuple(
    tuple(
        (_threshold_values[y * _TILE_SIZE + x] + 0.5)
        / (_TILE_SIZE * _TILE_SIZE)
        for x in range(_TILE_SIZE)
    )
    for y in range(_TILE_SIZE)
)


def _graphite_value(position: float) -> float:
    """Continuous graphite ramp used by the full-window background."""
    t = max(0.0, min(1.0, float(position)))
    # A continuous curve avoids the slope changes created by many discrete
    # gradient stops while keeping the original bright-top / near-black-bottom
    # appearance.
    return 1.0 + 51.0 * math.pow(1.0 - t, 2.08)


def build_graphite_surface(width: int, height: int) -> QImage:
    """Build a full-resolution, 1-LSB dithered background image.

    Qt's ordinary 8-bit gradient rasterization can expose visible contour bands
    on large dark displays. Here the final grayscale level is selected per pixel
    between the two nearest integer values, preserving the intended average
    brightness while breaking every contour into visually continuous texture.
    """
    width = max(1, int(width))
    height = max(1, int(height))
    bytes_per_line = width * 4
    pixels = bytearray(bytes_per_line * height)

    for y in range(height):
        position = y / max(1, height - 1)
        value = _graphite_value(position)
        low = int(math.floor(value))
        high = min(255, low + 1)
        fraction = value - low
        thresholds = _DITHER_THRESHOLDS[y % _TILE_SIZE]

        row_start = y * bytes_per_line
        for x in range(width):
            level = high if fraction > thresholds[x % _TILE_SIZE] else low
            offset = row_start + x * 4
            pixels[offset] = level
            pixels[offset + 1] = level
            pixels[offset + 2] = level
            pixels[offset + 3] = 255

    # copy() detaches the QImage from the temporary Python byte buffer.
    return QImage(
        bytes(pixels),
        width,
        height,
        bytes_per_line,
        QImage.Format_ARGB32,
    ).copy()
