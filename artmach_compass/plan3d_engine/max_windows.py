"""Map measured facade windows onto physical openings for every floor."""

from __future__ import annotations


def collect_all_floor_windows(panel, wall_floors):
    from plan3d_canonical_export import _cad_unit_info
    from plan3d_max_bridge import (
        _collect_ground_physical_windows, _ground_rect, _ground_side_mapping,
    )

    page = panel.parentWidget()
    viewport = getattr(page, "viewport", None)
    if viewport is None:
        raise RuntimeError("Window export: viewport unavailable")
    store = getattr(panel, "_analysis_results", {})
    analysis = store.get("facade_windows_all_floors", {})
    assignments = getattr(panel, "_assignments", {})
    plans = assignments.get("floor_plans", {})
    facades = assignments.get("facades", {})
    settings = getattr(panel, "_floor_settings", {})
    pivots = getattr(panel, "_floor_pivots", {})
    units = _cad_unit_info(viewport)
    results = []
    for wall_floor in wall_floors:
        floor_name = str(wall_floor["name"])
        if floor_name not in plans or floor_name not in settings:
            raise RuntimeError(f"Window export: {floor_name} lacks a plan or settings")
        pivot = dict(pivots.get(floor_name, {}))
        pivot.setdefault("pivot_x", float(wall_floor.get("pivot_x", 0)))
        pivot.setdefault("pivot_y", float(wall_floor.get("pivot_y", 0)))
        physical, stats, _ = _collect_ground_physical_windows(
            viewport, floor_name, plans[floor_name], pivot, settings[floor_name], units,
        )
        mapping = _ground_side_mapping(panel, floor_name)
        mapped = []
        for side in ("bottom", "top", "left", "right"):
            facade_name = mapping.get(side)
            if facade_name not in facades or facade_name not in analysis:
                raise RuntimeError(f"Window export: {floor_name}/{side} has no matched facade")
            left, _, right, _ = _ground_rect(facades[facade_name])
            width = max(right - left, 1e-9)
            measured = []
            for window in analysis[facade_name]["windows"]:
                if window["floor_name"] != floor_name:
                    continue
                center_x = (float(window["bbox"][0]) + float(window["bbox"][2])) / 2
                measured.append(((center_x - left) / width, window))
            measured.sort(key=lambda row: row[0])
            geometry = sorted((row for row in physical if row["side"] == side),
                              key=lambda row: row["pos"])
            if len(measured) != len(geometry):
                raise RuntimeError(
                    f"Window export: {floor_name}/{side}: "
                    f"{len(geometry)} physical, {len(measured)} facade windows"
                )
            for physical_row, (_, window) in zip(geometry, measured):
                sill = float(window["floor_local_sill_cm"])
                top = float(window["floor_local_top_cm"])
                if sill < -2 or top <= sill:
                    raise RuntimeError(f"Window export: invalid height on {floor_name}/{side}")
                a = list(physical_row["jamb_a_cm"])
                b = list(physical_row["jamb_b_cm"])
                width_cm = ((b[0]-a[0])**2 + (b[1]-a[1])**2)**.5
                mapped.append({
                    "window_id": f"W{len(mapped)+1:03d}", "jamb_a_cm": a,
                    "jamb_b_cm": b, "width_cm": width_cm,
                    "sill_cm": max(0., sill), "top_cm": top,
                    "height_cm": float(window["height_cm"]),
                    "facade": facade_name, "plan_side": side,
                    "source": "FACADE_FLOOR_DATUM",
                })
        results.append({
            "name": floor_name,
            "safe_name": str(wall_floor.get("safe_name", floor_name)),
            "base_z_cm": float(wall_floor.get("base_z_cm", 0)),
            "window_count": len(mapped), "windows": mapped,
            "physical_count": len(physical), "resolver_stats": stats,
        })
    return results
