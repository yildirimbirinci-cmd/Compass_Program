from dataclasses import dataclass

from PySide6.QtCore import Signal, Qt
from PySide6.QtGui import QResizeEvent
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLineEdit


@dataclass(frozen=True)
class ResponsiveSearchMetrics:
    profile: str
    width: int
    height: int
    bar_height: int
    top_margin: int
    side_margin: int
    font_size: int


def search_metrics_for_width(available_width: int) -> ResponsiveSearchMetrics:
    """Return deterministic responsive dimensions for the current viewport."""
    width = max(240, int(available_width))

    if width < 600:  # Phones and narrow portrait windows.
        side = 16
        return ResponsiveSearchMetrics(
            "phone", max(208, width - (side * 2)), 44, 60, 8, side, 14
        )

    if width < 1024:  # Tablets and compact landscape devices.
        side = 24
        target = min(680, max(420, int(width * 0.82)))
        return ResponsiveSearchMetrics("tablet", target, 46, 62, 8, side, 15)

    if width < 2200:  # Full-HD laptops and standard desktop windows.
        side = 32
        target = min(820, max(640, int(width * 0.52)))
        return ResponsiveSearchMetrics("desktop", target, 48, 64, 8, side, 16)

    # 2K/4K large desktop reference. Width is capped to preserve visual focus.
    side = 40
    target = min(900, max(820, int(width * 0.36)))
    return ResponsiveSearchMetrics("large_desktop", target, 48, 64, 8, side, 16)


class AppBar(QFrame):
    """Responsive Compass top bar containing only the centered global search."""

    search_changed = Signal(str)
    search_submitted = Signal(str)
    responsive_profile_changed = Signal(str)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("appBar")
        self._active_profile = ""

        self._row = QHBoxLayout(self)
        self._row.setSpacing(0)
        self._row.addStretch(1)

        self.search_input = QLineEdit(self)
        self.search_input.setObjectName("compassSearch")
        self.search_input.setPlaceholderText("Search Compass...")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.search_input.textChanged.connect(self.search_changed)
        self.search_input.returnPressed.connect(
            lambda: self.search_submitted.emit(self.search_input.text().strip())
        )
        self._row.addWidget(self.search_input, 0, Qt.AlignTop)
        self._row.addStretch(1)

        self.apply_responsive_layout(2560)

    @property
    def active_profile(self) -> str:
        return self._active_profile

    def apply_responsive_layout(self, available_width: int) -> None:
        metrics = search_metrics_for_width(available_width)
        self.setFixedHeight(metrics.bar_height)
        self._row.setContentsMargins(
            metrics.side_margin,
            metrics.top_margin,
            metrics.side_margin,
            metrics.bar_height - metrics.top_margin - metrics.height,
        )
        self.search_input.setFixedSize(metrics.width, metrics.height)
        self.search_input.setProperty("responsiveProfile", metrics.profile)
        self.search_input.setStyleSheet(
            f"font-size: {metrics.font_size}px; padding-left: 18px; padding-right: 18px;"
        )

        if metrics.profile != self._active_profile:
            self._active_profile = metrics.profile
            self.responsive_profile_changed.emit(metrics.profile)

    def resizeEvent(self, event: QResizeEvent) -> None:
        self.apply_responsive_layout(event.size().width())
        super().resizeEvent(event)
