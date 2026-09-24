import py_compile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CompassProjectTests(unittest.TestCase):
    def test_python_sources_compile(self):
        for source in ROOT.rglob('*.py'):
            py_compile.compile(str(source), doraise=True)

    def test_panel_order_is_left_middle_right(self):
        source = (ROOT / 'artmach_compass/ui/workspace.py').read_text(encoding='utf-8')
        self.assertIn('PANEL_ORDER = ("library_projects", "preview", "asset_inspector")', source)
        self.assertLess(source.index('self._layout.addWidget(self.left_panel'), source.index('self._layout.addWidget(self.center_panel'))
        self.assertLess(source.index('self._layout.addWidget(self.center_panel'), source.index('self._layout.addWidget(self.right_panel'))

    def test_tree_buttons_use_two_word_folder_labels(self):
        source = (ROOT / 'artmach_compass/core/library_catalog.py').read_text(encoding='utf-8')
        self.assertIn('compact_folder_name', source)

    def test_standby_runtime_is_removed(self):
        main = (ROOT / 'artmach_compass/ui/main_window.py').read_text(encoding='utf-8')
        workspace = (ROOT / 'artmach_compass/ui/workspace.py').read_text(encoding='utf-8')
        self.assertNotIn('_idle_timer', main)
        self.assertNotIn('installEventFilter', main)
        self.assertNotIn('class StandbyLogoPanel', workspace)
        self.assertNotIn('class StandbyDimmingLayer', workspace)
        self.assertNotIn('class OrbitBackdrop', workspace)
        self.assertNotIn('_paint_preview_orbits', workspace)

    def test_working_background_has_no_orbit_circles(self):
        workspace = (ROOT / 'artmach_compass/ui/workspace.py').read_text(encoding='utf-8')
        preview = workspace[workspace.index('class PreviewCanvas'):workspace.index('class CenterWorkspacePanel')]
        self.assertNotIn('drawEllipse', preview)
        self.assertNotIn('QRadialGradient', preview)

    def test_navigation_selection_uses_blue_text_and_marker_only(self):
        theme = (ROOT / "artmach_compass" / "ui" / "theme.py").read_text(encoding="utf-8")
        self.assertIn('QFrame#navigationRow[active="true"] {\n    /* Keep the same neutral button surface', theme)
        self.assertIn('QFrame#navigationMarker[active="true"] {\n    background: #47a6ff;', theme)
        self.assertIn('QLabel#navigationTitle[active="true"] {\n    color: #58adff;', theme)
        self.assertNotIn('border-left: 2px solid #47a6ff;', theme)

    def test_selected_buttons_are_not_orange(self):
        theme = (ROOT / 'artmach_compass/ui/theme.py').read_text(encoding='utf-8')
        active = theme[theme.rindex('QFrame#navigationRow[active="true"]'):]
        self.assertIn('#47a6ff', active)
        self.assertNotIn('rgba(142,78,0', active)
        self.assertNotIn('border-left: 2px solid #ff8a00', active)

    def test_button_fonts_are_two_pixels_larger(self):
        theme = (ROOT / 'artmach_compass/ui/theme.py').read_text(encoding='utf-8')
        self.assertIn('QToolButton,\nQPushButton {\n    font-size: 14px;', theme)
        self.assertIn('QLabel#navigationTitle {\n    color: #c1c7cb;\n    font-size: 12px;', theme)
        self.assertIn('QPushButton#topModeButton', theme)
        self.assertIn('font-size: 12px;', theme)

    def test_version_is_consistent(self):
        expected = '0.6.4'
        for relative in ('README.md', 'README_MINIMAL_UI.md', 'PROJECT_STRUCTURE.md', 'installer/ArtmachCompass.iss'):
            self.assertIn(expected, (ROOT / relative).read_text(encoding='utf-8'))

    def test_scrollbar_interaction_area_stays_12px(self):
        theme = (ROOT / 'artmach_compass/ui/theme.py').read_text(encoding='utf-8')
        self.assertIn('QScrollBar:vertical {\n    width: 12px;', theme)
        self.assertIn('QScrollBar:horizontal {\n    height: 12px;', theme)


if __name__ == '__main__':
    unittest.main()


def test_workspace_configured_roots_are_defined():
    source = (ROOT / "artmach_compass" / "ui" / "workspace.py").read_text(encoding="utf-8")
    assert "LIBRARY_ROOT = configured_library_path()" in source
    assert "PROJECT_ROOT = configured_project_path()" in source


def test_thumbnail_browser_only_shows_01_images():
    source = (ROOT / "artmach_compass" / "ui" / "workspace.py").read_text(encoding="utf-8")
    manager = (ROOT / "artmach_compass" / "core" / "thumbnail_manager.py").read_text(encoding="utf-8")
    assert "THUMBNAIL_MANAGER.is_01_image(asset[3])" in source
    assert "def is_01_image" in manager


def test_thumbnail_cards_are_compact():
    source = (ROOT / "artmach_compass" / "ui" / "workspace.py").read_text(encoding="utf-8")
    assert "DESKTOP_COLUMNS = 5" in source
    assert "GRID_GAP = 12" in source
    assert "min(150" in source

class ThumbnailMaxPairingTests(unittest.TestCase):
    def test_selected_thumbnail_resolves_single_max_in_asset_folder(self):
        import tempfile
        from artmach_compass.core.asset_pairing import resolve_max_for_thumbnail
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "Chair_01.jpg"
            model = root / "Chair.max"
            image.write_bytes(b"image")
            model.write_bytes(b"max")
            self.assertEqual(resolve_max_for_thumbnail(image), model)

    def test_preview_subfolder_resolves_matching_parent_max(self):
        import tempfile
        from artmach_compass.core.asset_pairing import resolve_max_for_thumbnail
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            previews = root / "Preview"
            previews.mkdir()
            image = previews / "Sofa_01.png"
            model = root / "Sofa.max"
            image.write_bytes(b"image")
            model.write_bytes(b"max")
            self.assertEqual(resolve_max_for_thumbnail(image), model)

    def test_ambiguous_unmatched_max_files_are_rejected(self):
        import tempfile
        from artmach_compass.core.asset_pairing import resolve_max_for_thumbnail
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            image = root / "Unknown_01.jpg"
            image.write_bytes(b"image")
            (root / "Chair.max").write_bytes(b"max")
            (root / "Table.max").write_bytes(b"max")
            self.assertIsNone(resolve_max_for_thumbnail(image))


def test_max_export_converts_renderer_materials_to_fbx_safe_materials():
    source = (ROOT / 'artmach_compass/conversion_engine/maxscripts/run_job.ms').read_text(encoding='utf-8')
    assert 'fn convertMaterialForExport' in source
    assert 'fn findDiffuseBitmap' in source
    assert 'result.material = convertMaterialForExport sourceNode.material' in source
    assert 'FBXExporterSetParam "EmbedTextures" true' in source
    assert 'fn normalizedTexturePath' in source
    assert 'pathConfig.resolvePath' in source
    assert 'bitmapTexture filename:sourcePath' in source
    assert '#texmapBaseColor' in source
    assert 'if childSuper == textureMap then (' in source
    assert ') else if isKindOf child Array then (' in source
    assert 'if childSuper == textureMap do (' not in source


def test_maxscript_has_no_ambiguous_do_else_boundary():
    """Max 2020 batch mode must never parse a `) else (` boundary here."""
    project_root = Path(__file__).resolve().parents[1]
    script = (project_root / "artmach_compass" / "conversion_engine" / "maxscripts" / "run_job.ms").read_text(encoding="utf-8")
    assert "if exportBitmap != undefined do (" in script
    assert "if exportBitmap == undefined do (" in script
    assert ") else (\n        format \"COMPASS_ENGINE: No diffuse texture found" not in script


def test_failed_conversion_creates_complete_diagnostics_bundle_code_path():
    source = (ROOT / "artmach_compass" / "conversion_engine" / "engine" / "pipeline.py").read_text(encoding="utf-8")
    assert "_create_diagnostics_bundle" in source
    assert "run_job_deployed_numbered.txt" in source
    assert "diagnostic_summary.json" in source
    assert "README_SEND_THIS_ZIP.txt" in source
    assert "diagnostics_zip" in source



def test_diagnostics_are_written_to_easy_to_find_folder_and_latest_alias():
    source = (ROOT / "artmach_compass" / "conversion_engine" / "engine" / "pipeline.py").read_text(encoding="utf-8")
    assert 'self.runtime_root / "logs"' in source
    assert 'Latest_Diagnostics.zip' in source
    assert 'Latest_Diagnostics.txt' in source


def test_preview_failure_opens_diagnostics_folder():
    source = (ROOT / "artmach_compass" / "ui" / "workspace.py").read_text(encoding="utf-8")
    worker = (ROOT / "artmach_compass" / "core" / "preview_generator.py").read_text(encoding="utf-8")
    assert 'failed = Signal(str, str)' in worker
    assert 'QDesktopServices.openUrl' in source
    assert 'Diagnostic ZIP created' in source


def test_preview_thread_creates_diagnostics_before_pipeline_starts():
    source = Path("artmach_compass/core/preview_generator.py").read_text(encoding="utf-8")
    assert "_write_emergency_diagnostics" in source
    assert 'runtime_root / "logs"' in source
    assert 'Latest_Diagnostics.zip' in source
    assert 'Latest_Diagnostics.txt' in source


def test_textureless_success_also_creates_diagnostics_bundle():
    source = (ROOT / "artmach_compass" / "conversion_engine" / "engine" / "pipeline.py").read_text(encoding="utf-8")
    assert 'material_count > 0 and image_count == 0' in source
    assert 'GLB validation warning: materials were exported but no texture images' in source
    assert 'report.diagnostics_zip = str(diagnostics)' in source


def test_corona_legacy_materials_use_native_subtexmap_traversal():
    source = (ROOT / "artmach_compass" / "conversion_engine" / "maxscripts" / "run_job.ms").read_text(encoding="utf-8")
    assert "getNumSubTexmaps ownerValue" in source
    assert "getSubTexmap ownerValue index" in source
    assert "getSubTexmapSlotName ownerValue index" in source
    assert "Base texture slot matched" in source
    assert "Fallback texture slot matched" in source
