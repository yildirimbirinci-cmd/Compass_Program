"""Run with PySide6 installed to check the actual Compass tool-panel layout."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from artmach_compass.ui.workspace import CompassWorkspace, ProjectDetailsPanel
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
            for title in ("Layers", "Properties", "Project Details"):
                workspace._handle_plan3d_command(title)
                self.app.processEvents()
                self.assertTrue(center._plan3d_tools.isVisible())
                self.assertTrue(center._plan3d_tools._panels[title].isVisible())
            center._plan3d_tools.close_panel("Layers")
            self.app.processEvents()
            self.assertEqual(tuple(center._plan3d_tools._panels), ("Properties", "Project Details"))
            workspace._handle_plan3d_command("Layers")
            self.app.processEvents()
            self.assertEqual([center._plan3d_tools._layout.itemAt(i).widget().title
                              for i in range(center._plan3d_tools._layout.count())],
                             ["Layers", "Properties", "Project Details"])
            for title in ("Layers", "Properties", "Project Details"):
                center._plan3d_tools.close_panel(title)
            self.app.processEvents()
            self.assertFalse(center._plan3d_tools.isVisible())
        finally:
            workspace.close()

    def test_project_details_requires_all_assigned_parameters(self):
        panel = ProjectDetailsPanel()
        try:
            self.assertFalse(panel.confirm_button.isEnabled())
            self.assertFalse(panel.create_button.isEnabled())
            panel.floor_tab.click()
            self.assertTrue(panel.floor_group.isVisibleTo(panel))
            panel._viewport = object()
            panel._assignments["facades"] = {name: [0, 0, 10, 10] for name in panel.FACADES}
            panel._assignments["floor_plans"] = {"Ground Floor": [0, 0, 10, 10]}
            panel._update_buttons()
            self.assertFalse(panel.confirm_button.isEnabled())
            panel.dimensions["floor_elevation_cm"].setText("0")
            panel.dimensions["wall_height_cm"].setText("280")
            panel.dimensions["door_height_cm"].setText("210")
            panel._update_buttons()
            self.assertFalse(panel.confirm_button.isEnabled())
            panel._floor_pivots["Ground Floor"] = {"pivot_x": 0, "pivot_y": 0}
            panel._update_buttons()
            self.assertTrue(panel.confirm_button.isEnabled())
            panel.confirm_details()
            self.assertTrue(panel.create_button.isEnabled())
            panel.dimensions["wall_height_cm"].setText("290")
            self.assertFalse(panel.create_button.isEnabled())
        finally:
            panel.close()


if __name__ == "__main__":
    unittest.main()
