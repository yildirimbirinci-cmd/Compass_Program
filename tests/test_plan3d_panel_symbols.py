"""Catch missing panel controls before users click Tools in Compass."""

import ast
from pathlib import Path
import unittest


class Plan3DPanelSymbolTests(unittest.TestCase):
    def test_panel_controls_are_defined_before_widget_construction(self):
        source = Path(__file__).resolve().parents[1] / "artmach_compass/ui/workspace.py"
        module = ast.parse(source.read_text(encoding="utf-8"))
        classes = {node.name: node.lineno for node in module.body
                   if isinstance(node, ast.ClassDef)}
        for name in ("Plan3DEyeButton", "Plan3DPanelButton", "Plan3DLayerRow"):
            with self.subTest(name=name):
                self.assertIn(name, classes)
                self.assertLess(classes[name], classes["Plan3DToolPanel"])


if __name__ == "__main__":
    unittest.main()
