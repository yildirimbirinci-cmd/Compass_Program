"""Facade window heights from the Plan3D logical opening detector.

Coordinates are read from the source drawing.  Each facade uses its own
lowest horizontal measurement line; every storey uses that same facade datum.
"""

from __future__ import annotations

import math
import unicodedata


def _layer_name(value):
    return unicodedata.normalize("NFC", str(value or "").strip()).casefold()


def _bounds(rect):
    x, y, width, height = (float(value) for value in rect)
    return min(x, x + width), min(y, y + height), max(x, x + width), max(y, y + height)


def facade_datum(document, rect, *, measurement_layer="C Ölçü"):
    """Select the lowest real horizontal measurement segment inside a facade."""
    left, bottom, right, top = _bounds(rect)
    candidates = []
    for entity in document.modelspace():
        if _layer_name(getattr(entity.dxf, "layer", "")) != _layer_name(measurement_layer):
            continue
        kind = entity.dxftype()
        if kind == "LINE":
            points = [(float(entity.dxf.start.x), float(entity.dxf.start.y)),
                      (float(entity.dxf.end.x), float(entity.dxf.end.y))]
        elif kind == "LWPOLYLINE":
            points = [(float(x), float(y)) for x, y in entity.get_points("xy")]
        elif kind == "POLYLINE":
            points = [(float(v.dxf.location.x), float(v.dxf.location.y)) for v in entity.vertices]
        else:
            continue
        pairs = list(zip(points, points[1:]))
        if kind != "LINE" and len(points) > 2 and (getattr(entity, "closed", False) or getattr(entity, "is_closed", False)):
            pairs.append((points[-1], points[0]))
        for (x0, y0), (x1, y1) in pairs:
            length = abs(x1 - x0)
            if length <= 1e-9 or abs(y1 - y0) > max(1e-9, length * .015):
                continue
            # The segment must belong to the selected facade, not its neighbour.
            if min(x0, x1) < left - 1e-9 or max(x0, x1) > right + 1e-9:
                continue
            if min(y0, y1) < bottom - 1e-9 or max(y0, y1) > top + 1e-9:
                continue
            candidates.append({"start": [x0, y0], "end": [x1, y1],
                               "y": (y0 + y1) / 2, "length": length,
                               "layer": measurement_layer})
    if not candidates:
        raise ValueError(f"No horizontal measurement line on {measurement_layer!r} in this facade")
    return min(candidates, key=lambda row: (row["y"], -row["length"], min(row["start"][0], row["end"][0])))


def analyze_window_heights(viewport, facade_rects, floor_settings, *, measurement_layer="C Ölçü", cad_to_cm=None):
    """Analyze every matched facade without introducing any user-interface controls.

    `facade_rects` maps facade names to the existing Plan3D x,y,w,h selections.
    Only openings the existing layer-driven detector identified as Window count.
    A floor name must already be assigned by that detector; ambiguous records
    fail explicitly rather than being silently placed on an incorrect floor.
    """
    if cad_to_cm is None:
        from src.app.plan3d_canonical_export import _cad_unit_info
        cad_to_cm = _cad_unit_info(viewport)["to_cm"]
    cad_to_cm = float(cad_to_cm)
    if not math.isfinite(cad_to_cm) or cad_to_cm <= 0:
        raise ValueError("Invalid CAD unit scale")
    document = getattr(viewport, "_document", None)
    if document is None:
        raise ValueError("No CAD drawing is open")
    result = {}
    for facade_name, rect in facade_rects.items():
        datum = facade_datum(document, rect, measurement_layer=measurement_layer)
        payload = viewport.analyze_facade_matching_inputs(rect, floor_settings)
        windows = []
        for opening in payload.get("logical_openings", ()):
            if opening.get("semantic_type") != "Window":
                continue
            floor_name = opening.get("floor_name")
            if floor_name not in floor_settings:
                raise ValueError(f"Window on {facade_name} has no confirmed floor")
            box = opening.get("bbox")
            if not isinstance(box, (tuple, list)) or len(box) < 4:
                raise ValueError(f"Window on {facade_name} has no valid bounds")
            y0, y1 = sorted((float(box[1]), float(box[3])))
            if not all(map(math.isfinite, (y0, y1))) or y1 <= y0:
                raise ValueError(f"Window on {facade_name} has invalid height")
            base_z = float(floor_settings[floor_name]["floor_elevation_cm"])
            sill_z = (y0 - datum["y"]) * cad_to_cm
            top_z = (y1 - datum["y"]) * cad_to_cm
            row = dict(opening)
            row.update(facade=facade_name, floor_name=floor_name,
                       datum_y=datum["y"], datum_source=measurement_layer,
                       floor_local_sill_cm=sill_z - base_z,
                       floor_local_top_cm=top_z - base_z,
                       sill_z_cm=sill_z, top_z_cm=top_z,
                       height_cm=top_z - sill_z)
            windows.append(row)
        result[facade_name] = {"datum_line": datum, "windows": windows}
    return result
