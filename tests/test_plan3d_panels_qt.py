"""Run with PySide6 installed to check the actual Compass tool-panel layout."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from artmach_compass.ui.workspace import CompassWorkspace
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication is not None, "PySide6/Qt3D is unavailable")
class Plan3DPanelVisibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_open_close_and_reopen_in_fixed_order(self):
        workspace = CompassWorkspace()
        workspace.resize(1500, 850)
        workspace.show()
        try:
            center = workspace.center_panel
            self.assertFalse(center._plan3d_tools.isVisible())
            for title in ("Layers", "Properties", "Export Details"):
                workspace._handle_plan3d_command(title)
                self.app.processEvents()
                self.assertTrue(center._plan3d_tools.isVisible())
                self.assertTrue(center._plan3d_tools._panels[title].isVisible())
            center._plan3d_tools.close_panel("Layers")
            self.app.processEvents()
            self.assertEqual(tuple(center._plan3d_tools._panels), ("Properties", "Export Details"))
            workspace._handle_plan3d_command("Layers")
            self.app.processEvents()
            self.assertEqual([center._plan3d_tools._layout.itemAt(i).widget().title
                              for i in range(center._plan3d_tools._layout.count())],
                             ["Layers", "Properties", "Export Details"])
            for title in ("Layers", "Properties", "Export Details"):
                center._plan3d_tools.close_panel(title)
            self.app.processEvents()
            self.assertFalse(center._plan3d_tools.isVisible())
        finally:
            workspace.close()


if __name__ == "__main__":
    unittest.main()
