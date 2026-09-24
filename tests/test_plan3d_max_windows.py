import sys
import types
import unittest
from unittest.mock import patch

from artmach_compass.plan3d_engine.max_windows import collect_all_floor_windows


class MaxWindowTests(unittest.TestCase):
    def test_each_floor_receives_its_own_local_sill_and_base_z(self):
        canon = types.ModuleType("plan3d_canonical_export")
        canon._cad_unit_info = lambda viewport: {"to_cm": 1}
        bridge = types.ModuleType("plan3d_max_bridge")
        bridge._ground_rect = lambda rect: (rect[0], rect[1], rect[0] + rect[2], rect[1] + rect[3])
        bridge._ground_side_mapping = lambda panel, floor: {"bottom": "Front", "top": "Rear", "left": "Left", "right": "Right"}
        bridge._collect_ground_physical_windows = lambda viewport, floor, *args: (
            [{"side": "bottom", "pos": .2, "jamb_a_cm": [0, 0], "jamb_b_cm": [10, 0]}],
            {}, {},
        )
        facades = {name: (0, 0, 100, 1000) for name in ("Front", "Rear", "Left", "Right")}
        panel = types.SimpleNamespace(
            parentWidget=lambda: types.SimpleNamespace(viewport=object()),
            _assignments={"floor_plans": {"Ground Floor": (0, 0, 100, 100), "First Floor": (0, 0, 100, 100)}, "facades": facades},
            _floor_settings={"Ground Floor": {}, "First Floor": {}},
            _floor_pivots={},
            _analysis_results={"facade_windows_all_floors": {
                name: {"windows": [
                    {"floor_name": floor, "bbox": [10, 0, 30, 10],
                     "floor_local_sill_cm": 60, "floor_local_top_cm": 240, "height_cm": 180}
                    for floor in ("Ground Floor", "First Floor")
                ] if name == "Front" else []} for name in facades}},
        )
        floors = [{"name": "Ground Floor", "base_z_cm": 0},
                  {"name": "First Floor", "base_z_cm": 315}]
        with patch.dict(sys.modules, {"plan3d_canonical_export": canon, "plan3d_max_bridge": bridge}):
            output = collect_all_floor_windows(panel, floors)
        self.assertEqual([floor["window_count"] for floor in output], [1, 1])
        self.assertEqual([floor["base_z_cm"] for floor in output], [0, 315])
        self.assertEqual([floor["windows"][0]["sill_cm"] for floor in output], [60, 60])


if __name__ == "__main__":
    unittest.main()
