import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ActiveOnlyRuntimeSourceTests(unittest.TestCase):
    def test_application_opens_directly_in_working_mode(self):
        source = (ROOT / 'artmach_compass/ui/main_window.py').read_text(encoding='utf-8')
        self.assertIn('self._standby_active = False', source)
        self.assertIn('def is_standby_active', source)
        self.assertIn('return False', source)

    def test_center_uses_fixed_7_9_over_8_layout(self):
        source = (ROOT / 'artmach_compass/ui/workspace.py').read_text(encoding='utf-8')
        self.assertNotIn('QSplitter(', source)
        self.assertIn('top_layout.addWidget(self._thumbnail_frame, 1)', source)
        self.assertIn('top_layout.addWidget(self._viewer_frame, 1)', source)
        self.assertIn('layout.addWidget(top_row, 3)', source)
        self.assertIn('layout.addWidget(self._detail_panel, 2)', source)
        self.assertIn('scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)', source)
        self.assertIn('scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)', source)


if __name__ == '__main__':
    unittest.main()
