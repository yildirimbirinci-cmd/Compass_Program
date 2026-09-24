import os
import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from artmach_compass.core.app_logging import get_logger, setup_logging
from artmach_compass.ui.main_window import CompassMainWindow
from artmach_compass.ui.theme import APP_STYLESHEET


def resource_path(relative_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, relative_path)


def main() -> int:
    log_path = setup_logging()
    logger = get_logger()

    QCoreApplication.setOrganizationName("Artmach")
    QCoreApplication.setApplicationName("Artmach Compass")
    QCoreApplication.setApplicationVersion("0.6.1")
    # Required for the Qt3D viewport (embedded via createWindowContainer in
    # Model3DViewer) to render correctly alongside the rest of the widget UI.
    # Without this, the embedded Qt3D window commonly shows as blank/black.
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    icon = QIcon(resource_path("resources/icons/ArtmachCompass.ico"))
    app.setWindowIcon(icon)

    window = CompassMainWindow(icon)
    window.showMaximized()
    logger.info("Main window shown. Log file: %s", log_path)
    try:
        exit_code = app.exec()
    except Exception:
        logger.exception("Application crashed while running the Qt event loop")
        raise
    logger.info("=== Artmach Compass session ended (exit code %s) ===", exit_code)
    return exit_code
