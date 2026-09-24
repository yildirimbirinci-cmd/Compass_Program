from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap, QResizeEvent
from PySide6.QtWidgets import QMainWindow, QWidget

from artmach_compass.ui.gradient_surface import build_graphite_surface
from artmach_compass.ui.workspace import CompassWorkspace


class GradientBackdrop(QWidget):
    """One continuous, full-resolution graphite surface."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("minimalWorkspace")
        self.setAttribute(Qt.WA_OpaquePaintEvent, True)
        self._surface = build_graphite_surface(1, 1)
        self._surface_size = (1, 1)

    def _rebuild_surface(self) -> None:
        size = (max(1, self.width()), max(1, self.height()))
        if size == self._surface_size:
            return
        self._surface = build_graphite_surface(*size)
        self._surface_size = size

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._rebuild_surface()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        self._rebuild_surface()
        painter = QPainter(self)
        painter.drawImage(0, 0, self._surface)


class CompassMainWindow(QMainWindow):
    """Full-bleed Compass shell. Standby mode is permanently disabled."""

    MINIMUM_WIDTH = 320
    MINIMUM_HEIGHT = 480
    DEFAULT_WIDTH = 1440
    DEFAULT_HEIGHT = 900
    IDLE_TIMEOUT_MS = 5_000



    def __init__(self, icon: QIcon, *, idle_timeout_ms: int | None = None) -> None:
        super().__init__()
        self.setWindowTitle("\u200b")
        # Keep the native Windows title bar but render its icon slot fully transparent.
        transparent_icon = QPixmap(1, 1)
        transparent_icon.fill(Qt.transparent)
        self.setWindowIcon(QIcon(transparent_icon))
        self.setWindowFlags(
            Qt.Window
            | Qt.WindowTitleHint
            | Qt.WindowSystemMenuHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
            | Qt.WindowCloseButtonHint
        )
        self.setMinimumSize(self.MINIMUM_WIDTH, self.MINIMUM_HEIGHT)
        self.resize(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

        self.central = GradientBackdrop(self)
        self.setCentralWidget(self.central)

        self.center = CompassWorkspace(self.central)

        self._standby_active = False

        self._update_geometry(self.DEFAULT_WIDTH, self.DEFAULT_HEIGHT)

    @property
    def is_standby_active(self) -> bool:
        return False

    def resizeEvent(self, event: QResizeEvent) -> None:
        self._update_geometry(event.size().width(), event.size().height())
        super().resizeEvent(event)

    def closeEvent(self, event) -> None:
        super().closeEvent(event)

    def _update_geometry(self, width: int, height: int) -> None:
        width = max(self.MINIMUM_WIDTH, int(width))
        height = max(self.MINIMUM_HEIGHT, int(height))

        # Search is intentionally detached from the shell until its new
        # location is approved. The workspace therefore owns every pixel of
        # the window.
        self.center.setGeometry(0, 0, width, height)
