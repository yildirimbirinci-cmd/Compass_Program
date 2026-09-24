import unittest
from types import SimpleNamespace

from artmach_compass.plan3d_engine.window_heights import analyze_window_heights, facade_datum


def line(layer, x0, y0, x1, y1):
    return SimpleNamespace(
        dxf=SimpleNamespace(layer=layer, start=SimpleNamespace(x=x0, y=y0),
                            end=SimpleNamespace(x=x1, y=y1)),
        dxftype=lambda: "LINE",
    )


class Drawing:
    def __init__(self):
        self.lines = [line("C Ölçü", 0, 100, 90, 100),
                      line("C Ölçü", 100, 500, 190, 500),
                      line("C Ölçü", 0, 250, 90, 250)]

    def modelspace(self):
        return self.lines


class Viewport:
    def __init__(self):
        self._document = Drawing()

    def analyze_facade_matching_inputs(self, rect, settings):
        x = rect[0]
        datum = 100 if x == 0 else 500
        return {"logical_openings": [
            {"semantic_type": "Window", "floor_name": "Ground Floor",
             "bbox": [x + 10, datum + 60, x + 30, datum + 240]},
            {"semantic_type": "Window", "floor_name": "First Floor",
             "bbox": [x + 35, datum + 375, x + 55, datum + 555]},
        ]}


class WindowHeightTests(unittest.TestCase):
    def test_each_facade_uses_own_lowest_datum_and_each_floor_uses_own_base(self):
        settings = {"Ground Floor": {"floor_elevation_cm": 0},
                    "First Floor": {"floor_elevation_cm": 315}}
        output = analyze_window_heights(
            Viewport(), {"Front": (0, 95, 90, 600), "Rear": (100, 495, 90, 600)},
            settings, cad_to_cm=1,
        )
        for facade, expected_y in (("Front", 100), ("Rear", 500)):
            self.assertEqual(output[facade]["datum_line"]["y"], expected_y)
            first, upper = output[facade]["windows"]
            self.assertEqual((first["floor_local_sill_cm"], first["height_cm"]), (60, 180))
            self.assertEqual((upper["floor_local_sill_cm"], upper["sill_z_cm"], upper["height_cm"]), (60, 375, 180))

    def test_missing_measurement_line_fails_instead_of_using_adjacent_facade(self):
        with self.assertRaisesRegex(ValueError, "No horizontal measurement line"):
            facade_datum(Drawing(), (200, 0, 100, 600))

    def test_missing_floor_is_not_silently_assigned(self):
        class Unassigned(Viewport):
            def analyze_facade_matching_inputs(self, rect, settings):
                return {"logical_openings": [{"semantic_type": "Window", "bbox": [10, 160, 20, 220]}]}
        with self.assertRaisesRegex(ValueError, "no confirmed floor"):
            analyze_window_heights(Unassigned(), {"Front": (0, 95, 90, 600)},
                                   {"Ground Floor": {"floor_elevation_cm": 0}}, cad_to_cm=1)


if __name__ == "__main__":
    unittest.main()
