from __future__ import annotations

import math
import json
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

from artmach_compass.core.thumbnail_manager import ThumbnailManager
from artmach_compass.core.asset_pairing import resolve_max_for_thumbnail
from artmach_compass.core.preview_generator import PreviewGenerationThread
from artmach_compass.core.app_logging import get_logger
from artmach_compass.ui.model_viewer import Model3DViewer
from artmach_compass.plan3d_embedded import create_embedded_plan3d_viewport

from artmach_compass.core.library_catalog import (
    configured_library_path,
    configured_project_path,
    compact_folder_name,
    display_folder_name,
    scan_category_assets,
    scan_child_folders,
)

from PySide6.QtCore import (
    QAbstractAnimation,
    QEvent,
    QEasingCurve,
    QPoint,
    QPointF,
    Property,
    QRect,
    QRectF,
    QPropertyAnimation,
    QTimer,
    Qt,
    Signal,
    QUrl,
)
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QFontMetrics,
    QImage,
    QLinearGradient,
    QPainter,
    QTransform,
    QPainterPath,
    QPen,
    QPixmap,
    QPixmapCache,
    QRadialGradient,
    QDesktopServices,
    QDoubleValidator,
)
from PySide6.QtWidgets import (
    QBoxLayout,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QLineEdit,
    QFileDialog,
    QMessageBox,
    QListWidget,
    QListWidgetItem,
    QWidgetAction,
    QMenu,
    QToolButton,
    QScrollArea,
    QScrollBar,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

LIBRARY_ROOT = configured_library_path()
PROJECT_ROOT = configured_project_path()
ASSET_CATALOG: dict[str, tuple[tuple[str, str, str, str], ...]] = {}




def _label(text: str, object_name: str) -> QLabel:
    widget = QLabel(text)
    widget.setObjectName(object_name)
    widget.setAttribute(Qt.WA_TransparentForMouseEvents, True)
    return widget


class NavigationRow(QFrame):
    """One selectable Library/Projects navigation row."""

    clicked = Signal(str)

    def __init__(
        self,
        title: str,
        detail: str = "",
        *,
        active: bool = False,
        key: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("navigationRow")
        compact = parent is not None and parent.objectName() == "folderRowHeader"
        self.setFixedHeight(26 if compact else 32)
        self.key = key or title
        self._active = active
        self.setProperty("active", active)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_Hover, True)
        self._hovered = False
        self._glow_phase = 0.0
        self._glow_timer = QTimer(self)
        self._glow_timer.setInterval(16)
        self._glow_timer.timeout.connect(self._advance_glow)

        row = QHBoxLayout(self)
        row.setContentsMargins(10, 4 if compact else 7, 9, 4 if compact else 7)
        row.setSpacing(9)

        marker = QFrame(self)
        marker.setObjectName("navigationMarker")
        marker.setProperty("active", active)
        marker.setFixedSize(5, 5)
        marker.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        marker_glow = QGraphicsDropShadowEffect(marker)
        marker_glow.setBlurRadius(0.0)
        marker_glow.setOffset(0.0, 0.0)
        marker_glow.setColor(QColor(69, 142, 218, 0))
        marker.setGraphicsEffect(marker_glow)
        self._marker = marker
        self._marker_glow = marker_glow
        row.addWidget(marker, 0, Qt.AlignVCenter)

        title_label = _label(title, "navigationTitle")
        title_label.setProperty("active", active)
        title_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        title_glow = QGraphicsDropShadowEffect(title_label)
        title_glow.setBlurRadius(0.0)
        title_glow.setOffset(0.0, 0.0)
        title_glow.setColor(QColor(69, 142, 218, 0))
        title_label.setGraphicsEffect(title_glow)
        self._title_label = title_label
        self._title_glow = title_glow
        row.addWidget(title_label, 1)

        # Keep the full folder name available to the scroll area instead of
        # silently clipping it to the current panel width.
        minimum_width = (
            row.contentsMargins().left()
            + row.contentsMargins().right()
            + marker.width()
            + row.spacing()
            + title_label.sizeHint().width()
            + 4
        )
        # Keep a content-aware preferred width, then let each sibling button
        # group equalize itself to the widest member in that group.
        self._preferred_width = max(126, min(184, minimum_width + 44))
        self.setFixedWidth(self._preferred_width)

        if detail:
            detail_label = _label(detail, "navigationDetail")
            row.addWidget(detail_label, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.set_active(active)

    @property
    def is_active(self) -> bool:
        return self._active

    def set_active(self, active: bool) -> None:
        self._active = bool(active)
        self.setProperty("active", self._active)
        self._marker.setProperty("active", self._active)
        self._title_label.setProperty("active", self._active)
        self._marker.setProperty("hovered", self._hovered and not self._active)
        self._title_label.setProperty("hovered", self._hovered and not self._active)
        self._marker_glow.setBlurRadius(13.0 if self._active else 0.0)
        self._marker_glow.setColor(
            QColor(69, 142, 218, 210 if self._active else 0)
        )
        self._title_glow.setBlurRadius(12.0 if self._active else 0.0)
        self._title_glow.setColor(
            QColor(69, 142, 218, 190 if self._active else 0)
        )
        if self._active:
            if not self._glow_timer.isActive():
                self._glow_timer.start()
        else:
            self._glow_timer.stop()
            self._glow_phase = 0.0
        for widget in (self, self._marker, self._title_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
            widget.update()

    def _advance_glow(self) -> None:
        self._glow_phase = (self._glow_phase + 0.025) % math.tau
        self.update()

    def enterEvent(self, event: QEvent) -> None:
        self._hovered = True
        if not self._active:
            self._marker.setProperty("hovered", True)
            self._title_label.setProperty("hovered", True)
            for widget in (self._marker, self._title_label):
                widget.style().unpolish(widget)
                widget.style().polish(widget)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._hovered = False
        self._marker.setProperty("hovered", False)
        self._title_label.setProperty("hovered", False)
        for widget in (self._marker, self._title_label):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.update()
        super().leaveEvent(event)

    def paintEvent(self, event: QEvent) -> None:
        super().paintEvent(event)
        if not self._hovered and not self._active:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        outline = QRectF(self.rect()).adjusted(0.75, 0.75, -0.75, -0.75)
        path = QPainterPath()
        path.addRoundedRect(outline, 8.0, 8.0)

        if self._active:
            pulse = 0.5 + 0.5 * math.sin(self._glow_phase)
            glow_alpha = round(34 + pulse * 116)
            for width, factor in ((7.0, 0.18), (4.0, 0.32), (2.5, 0.48)):
                color = QColor(71, 166, 255, round(glow_alpha * factor))
                painter.setPen(QPen(color, width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(path)
            painter.setPen(QPen(QColor(71, 166, 255, 235), 1.0))
            painter.drawPath(path)
        elif self._hovered:
            for width, alpha in ((3.0, 24), (1.5, 46)):
                painter.setPen(QPen(QColor(255, 132, 34, alpha), width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
                painter.drawPath(path)
            painter.setPen(QPen(QColor(255, 132, 34, 235), 0.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
            painter.drawPath(path)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit(self.key)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class LibraryProjectTabs(QWidget):
    """Persistent Library / Project / AI tabs with one sliding indicator."""

    mode_requested = Signal(str)
    TAB_ORDER = ("library", "project", "plan3d", "ai")
    TAB_LABELS = {
        "library": "Library",
        "project": "Project",
        "plan3d": "Plan3D",
        "ai": "AI",
    }
    INDICATOR_WIDTH = 30.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedHeight(43)
        self.setCursor(Qt.ArrowCursor)
        self.setMouseTracking(True)
        self._mode = "library"
        self._indicator_offset = 0.0
        self._indicator_animation = QPropertyAnimation(
            self,
            b"indicatorOffset",
            self,
        )
        self._indicator_animation.setDuration(640)
        self._indicator_animation.setEasingCurve(QEasingCurve.InOutCubic)

    def get_indicator_offset(self) -> float:
        return self._indicator_offset

    def set_indicator_offset(self, value: float) -> None:
        self._indicator_offset = float(value)
        self.update()

    indicatorOffset = Property(
        float,
        get_indicator_offset,
        set_indicator_offset,
    )

    def set_mode(self, mode: str, *, animated: bool = True) -> None:
        mode = mode if mode in self.TAB_ORDER else "library"
        target = self._indicator_target(mode)
        self._mode = mode
        self._indicator_animation.stop()
        if animated:
            self._indicator_animation.setStartValue(self._indicator_offset)
            self._indicator_animation.setEndValue(target)
            self._indicator_animation.start()
        else:
            self._indicator_offset = target
            self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            requested = self._mode_at(event.position())
            if requested is not None:
                self.mode_requested.emit(requested)
                event.accept()
                return
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event) -> None:
        self.setCursor(
            Qt.PointingHandCursor
            if self._mode_at(event.position()) is not None
            else Qt.ArrowCursor
        )
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    def _tab_geometries(self) -> dict[str, QRectF]:
        tab_width = self.width() / len(self.TAB_ORDER)
        return {
            mode: QRectF(index * tab_width, 0.0, tab_width, self.height())
            for index, mode in enumerate(self.TAB_ORDER)
        }

    def _indicator_target(self, mode: str) -> float:
        geometry = self._tab_geometries()[mode]
        return geometry.center().x() - (self.INDICATOR_WIDTH / 2.0)

    def _mode_at(self, point: QPointF) -> str | None:
        for mode, geometry in self._tab_geometries().items():
            if geometry.contains(point):
                return mode
        return None

    def resizeEvent(self, event) -> None:
        if self._indicator_animation.state() != QAbstractAnimation.Running:
            self._indicator_offset = self._indicator_target(self._mode)
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        font = painter.font()
        font.setPointSizeF(10.0)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)

        for mode, geometry in self._tab_geometries().items():
            painter.setPen(
                QColor("#f0f0f0")
                if self._mode == mode
                else QColor("#8d8d8d")
            )
            label_rect = QRectF(
                geometry.left(),
                0.0,
                geometry.width(),
                26.0,
            )
            painter.drawText(
                label_rect,
                Qt.AlignHCenter | Qt.AlignVCenter,
                self.TAB_LABELS[mode],
            )

        indicator = QRectF(
            self._indicator_offset,
            34.0,
            self.INDICATOR_WIDTH,
            2.0,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(255, 132, 34))
        painter.drawRoundedRect(indicator, 1.0, 1.0)


class PanelFace(QFrame):
    """Simple flat navigation face used by the AI panel."""

    row_clicked = Signal(str)

    def __init__(self, *, eyebrow: str, title: str, subtitle: str,
                 rows: tuple[tuple[str, str], ...], footer: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("flipPanelFace")
        self.rows: dict[str, NavigationRow] = {}
        layout = QVBoxLayout(self)
        # Keep the left panel itself and the navigation button widths unchanged,
        # but let the scrollbar rail reach the panel's right-side alignment line.
        # The former 20 px outer right margin incorrectly pulled the rail inward.
        layout.setContentsMargins(20, 0, 0, 18)
        layout.setSpacing(0)
        subtitle_label = _label(subtitle, "panelSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
        layout.addSpacing(22)
        for index, (row_title, detail) in enumerate(rows):
            navigation_row = NavigationRow(row_title, detail, active=index == 0,
                                           key=row_title, parent=self)
            navigation_row.clicked.connect(self._select_row)
            self.rows[row_title] = navigation_row
            layout.addWidget(navigation_row)
            layout.addSpacing(6)
        layout.addStretch(1)
        layout.addWidget(_label(footer, "panelFooter"))

    def _select_row(self, key: str) -> None:
        for row_key, row in self.rows.items():
            row.set_active(row_key == key)
        self.row_clicked.emit(key)


class Plan3DMenuFace(QFrame):
    """Plan3D commands in the same left panel and NavigationRow style."""

    command_requested = Signal(str)
    MENUS = (
        ("File", ("New Project", "Open Project", "Save Project",
                  "Save As Project", "Close Project")),
        ("Edit", ("Undo", "Redo")),
        ("Tools", ("Layers", "Properties", "Project Details")),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("flipPanelFace")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 0, 0, 18)
        layout.setSpacing(4)
        self._groups: dict[str, QWidget] = {}
        self._commands: dict[str, NavigationRow] = {}
        for title, commands in self.MENUS:
            header = NavigationRow(title, parent=self)
            header.clicked.connect(self._toggle)
            layout.addWidget(header, 0, Qt.AlignLeft)
            children = QWidget(self)
            child_layout = QVBoxLayout(children)
            child_layout.setContentsMargins(14, 0, 0, 0)
            child_layout.setSpacing(4)
            for command in commands:
                row = NavigationRow(command, parent=children)
                row.clicked.connect(self._select_command)
                self._commands[command] = row
                child_layout.addWidget(row, 0, Qt.AlignLeft)
            children.hide()
            self._groups[title] = children
            layout.addWidget(children)
        layout.addStretch(1)

    def _toggle(self, title: str) -> None:
        group = self._groups[title]
        opening = not group.isVisible()
        for other in self._groups.values():
            other.hide()
        group.setVisible(opening)

    def _select_command(self, command: str) -> None:
        row = self._commands[command]
        row.set_active(True)
        QTimer.singleShot(240, lambda selected=row: selected.set_active(False))
        self.command_requested.emit(command)


class PrecisionScrollArea(QScrollArea):
    """Scroll area whose wheel movement is pixel-precise and predictable."""

    WHEEL_PIXELS_PER_NOTCH = 34

    def wheelEvent(self, event) -> None:
        bar = self.verticalScrollBar()
        if event.modifiers() & Qt.ShiftModifier and self.horizontalScrollBar().maximum() > 0:
            bar = self.horizontalScrollBar()

        pixel = event.pixelDelta()
        angle = event.angleDelta()
        if bar.orientation() == Qt.Vertical:
            pixel_amount = pixel.y()
            angle_amount = angle.y()
        else:
            pixel_amount = pixel.x() or pixel.y()
            angle_amount = angle.x() or angle.y()

        if pixel_amount:
            delta = -pixel_amount
        elif angle_amount:
            delta = -round((angle_amount / 120.0) * self.WHEEL_PIXELS_PER_NOTCH)
        else:
            super().wheelEvent(event)
            return

        bar.setValue(max(bar.minimum(), min(bar.maximum(), bar.value() + delta)))
        event.accept()


class ReactiveScrollBar(QScrollBar):
    """Minimal scrollbar with grayscale rail and direction-aware comet trail."""

    ORANGE = QColor(255, 132, 34)
    TRACK = QColor(104, 106, 110)
    INTERACTION_THICKNESS = 12
    PAINTED_THUMB_THICKNESS = 2.0

    def __init__(
        self,
        orientation: Qt.Orientation,
        parent: QWidget | None = None,
        *,
        hide_handle_when_idle: bool = False,
        gradient_track: bool = False,
    ) -> None:
        super().__init__(orientation, parent)
        self._hide_handle_when_idle = hide_handle_when_idle
        self._gradient_track = gradient_track
        self._last_value = self.value()
        self._motion_direction = 0
        self._trail_strength = 0.0
        self._visual_strength = 0.0
        self._dragging = False
        self._drag_press_axis = 0.0
        self._drag_press_value = self.value()
        self.setProperty("active", False)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        # Keep the orange thumb visually thin while giving the pointer a
        # comfortable transparent hit strip. The previous 5 px strip was too
        # narrow on high-resolution displays and forced pixel-perfect clicks.
        if orientation == Qt.Vertical:
            self.setFixedWidth(self.INTERACTION_THICKNESS)
        else:
            self.setFixedHeight(self.INTERACTION_THICKNESS)

        self._idle_timer = QTimer(self)
        self._idle_timer.setSingleShot(True)
        self._idle_timer.setInterval(120)
        self._idle_timer.timeout.connect(self._deactivate_if_idle)

        self._fade_timer = QTimer(self)
        self._fade_timer.setInterval(16)
        self._fade_timer.timeout.connect(self._fade_active_state)

        self._trail_timer = QTimer(self)
        self._trail_timer.setInterval(16)
        self._trail_timer.timeout.connect(self._fade_trail)

        self.valueChanged.connect(self._on_value_changed)
        self.sliderPressed.connect(self._activity)
        self.sliderReleased.connect(self._schedule_idle)

    def _axis_position(self, event) -> float:
        position = event.position()
        return float(position.y() if self.orientation() == Qt.Vertical else position.x())

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self.maximum() > self.minimum():
            axis = self._axis_position(event)
            rect = self.rect()
            track_length = (
                rect.height()
                if self.orientation() == Qt.Vertical
                else rect.width()
            )
            handle_length = min(64, track_length)
            available = max(1.0, float(track_length - handle_length))
            span = self.maximum() - self.minimum()

            # Clicking anywhere on the gray rail centers the orange handle on
            # that point and scrolls the connected panel there immediately.
            handle_start = max(
                0.0,
                min(available, axis - (handle_length / 2.0)),
            )
            target = self.minimum() + round((handle_start / available) * span)
            self.setValue(max(self.minimum(), min(self.maximum(), target)))

            # Continue as a normal drag from the new position so click-drag
            # remains smooth and does not jump a second time.
            self._dragging = True
            self._drag_press_axis = axis
            self._drag_press_value = self.value()
            self.setSliderDown(True)
            self._activity()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._dragging:
            rect = self.rect()
            fixed_length = min(64, rect.height() if self.orientation() == Qt.Vertical else rect.width())
            track_length = rect.height() if self.orientation() == Qt.Vertical else rect.width()
            available = max(1.0, float(track_length - fixed_length))
            span = max(1, self.maximum() - self.minimum())
            delta_pixels = self._axis_position(event) - self._drag_press_axis
            target = self._drag_press_value + round((delta_pixels / available) * span)
            self.setValue(max(self.minimum(), min(self.maximum(), target)))
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.LeftButton and self._dragging:
            self._dragging = False
            self.setSliderDown(False)
            self._schedule_idle()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event) -> None:
        pixel_delta = event.pixelDelta()
        angle_delta = event.angleDelta()
        if self.orientation() == Qt.Vertical:
            pixel_amount = pixel_delta.y()
            angle_amount = angle_delta.y()
        else:
            pixel_amount = pixel_delta.x() or pixel_delta.y()
            angle_amount = angle_delta.x() or angle_delta.y()
        if pixel_amount:
            step = -pixel_amount
        else:
            notches = angle_amount / 120.0
            step = -round(notches * max(1, self.pageStep() / 12.0))
        if step:
            self.setValue(round(self.value() + step))
            self._activity()
            event.accept()
            return
        super().wheelEvent(event)

    def _set_active(self, active: bool) -> None:
        active = bool(active)
        self.setProperty("active", active)
        if active:
            # Enter active state immediately so hover, drag and mouse-wheel
            # movement are acknowledged without perceptible delay.
            self._fade_timer.stop()
            self._visual_strength = 1.0
        self.update()

    def _activity(self, *_args) -> None:
        self._set_active(True)
        self._schedule_idle()

    def passive_activity(self) -> None:
        """Treat indirect wheel movement as full scrollbar activity."""
        self._activity()

    def _fade_active_state(self) -> None:
        # Return to the passive orange gradually after activity stops.
        self._visual_strength = max(0.0, self._visual_strength - 0.025)
        self.update()
        if self._visual_strength <= 0.0:
            self._fade_timer.stop()
            self.setProperty("active", False)

    def _on_value_changed(self, value: int) -> None:
        delta = value - self._last_value
        if delta:
            self._motion_direction = 1 if delta > 0 else -1
            self._trail_strength = 1.0
            if not self._trail_timer.isActive():
                self._trail_timer.start()
        self._last_value = value
        if self._dragging or self.isSliderDown() or self.underMouse():
            self._activity()
        else:
            self.passive_activity()

    def _fade_trail(self) -> None:
        self._trail_strength = max(0.0, self._trail_strength - 0.055)
        self.update()
        if self._trail_strength <= 0.0:
            self._trail_timer.stop()

    def _schedule_idle(self) -> None:
        self._idle_timer.start()

    def _deactivate_if_idle(self) -> None:
        if not self.underMouse() and not self.isSliderDown():
            if not self._fade_timer.isActive():
                self._fade_timer.start()

    def enterEvent(self, event: QEvent) -> None:
        self._idle_timer.stop()
        self._set_active(True)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent) -> None:
        self._schedule_idle()
        super().leaveEvent(event)

    def _draw_track(self, painter: QPainter, rect: QRect) -> None:
        if self.orientation() == Qt.Vertical:
            axis = rect.center().x()
            if self._gradient_track:
                gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
                gradient.setColorAt(0.0, QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 0))
                gradient.setColorAt(0.10, QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 118))
                gradient.setColorAt(0.50, QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 168))
                gradient.setColorAt(0.90, QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 118))
                gradient.setColorAt(1.0, QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 0))
                painter.setPen(QPen(QBrush(gradient), 1.5))
            else:
                painter.setPen(QPen(QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 115), 1.5))
            painter.drawLine(axis, rect.top(), axis, rect.bottom())
        else:
            axis = rect.center().y()
            painter.setPen(QPen(QColor(self.TRACK.red(), self.TRACK.green(), self.TRACK.blue(), 115), 1.5))
            painter.drawLine(rect.left(), axis, rect.right(), axis)

    def _draw_comet(self, painter: QPainter, rect: QRect, handle: QRect) -> None:
        if self._motion_direction == 0 or self._trail_strength <= 0.0:
            return
        strength = self._trail_strength
        alpha = int(235 * strength)
        tail_length = max(52.0, (150.0 if self.orientation() == Qt.Vertical else 190.0) * strength)

        if self.orientation() == Qt.Vertical:
            x = rect.center().x()
            if self._motion_direction > 0:  # moving down: tail follows above
                head = float(handle.top())
                tail = max(float(rect.top()), head - tail_length)
                gradient = QLinearGradient(0, tail, 0, head)
                gradient.setColorAt(0.0, QColor(255, 132, 34, 0))
                gradient.setColorAt(0.72, QColor(255, 132, 34, max(10, alpha // 3)))
                gradient.setColorAt(1.0, QColor(255, 132, 34, alpha))
                painter.setPen(QPen(QBrush(gradient), 3.0, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(x, tail), QPointF(x, head))
            else:  # moving up: tail follows below
                head = float(handle.bottom())
                tail = min(float(rect.bottom()), head + tail_length)
                gradient = QLinearGradient(0, head, 0, tail)
                gradient.setColorAt(0.0, QColor(255, 132, 34, alpha))
                gradient.setColorAt(0.28, QColor(255, 132, 34, max(10, alpha // 3)))
                gradient.setColorAt(1.0, QColor(255, 132, 34, 0))
                painter.setPen(QPen(QBrush(gradient), 3.0, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(x, head), QPointF(x, tail))
        else:
            y = rect.center().y()
            if self._motion_direction > 0:  # moving right: tail follows left
                head = float(handle.left())
                tail = max(float(rect.left()), head - tail_length)
                gradient = QLinearGradient(tail, 0, head, 0)
                gradient.setColorAt(0.0, QColor(255, 132, 34, 0))
                gradient.setColorAt(0.72, QColor(255, 132, 34, max(10, alpha // 3)))
                gradient.setColorAt(1.0, QColor(255, 132, 34, alpha))
                painter.setPen(QPen(QBrush(gradient), 3.0, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(tail, y), QPointF(head, y))
            else:  # moving left: tail follows right
                head = float(handle.right())
                tail = min(float(rect.right()), head + tail_length)
                gradient = QLinearGradient(head, 0, tail, 0)
                gradient.setColorAt(0.0, QColor(255, 132, 34, alpha))
                gradient.setColorAt(0.28, QColor(255, 132, 34, max(10, alpha // 3)))
                gradient.setColorAt(1.0, QColor(255, 132, 34, 0))
                painter.setPen(QPen(QBrush(gradient), 3.0, Qt.SolidLine, Qt.RoundCap))
                painter.drawLine(QPointF(head, y), QPointF(tail, y))

    def _fixed_handle_rect(self, rect: QRect) -> QRect:
        fixed_length = 64
        if self.orientation() == Qt.Vertical:
            available = max(1, rect.height() - fixed_length)
        else:
            available = max(1, rect.width() - fixed_length)
        span = max(1, self.maximum() - self.minimum())
        ratio = (self.value() - self.minimum()) / span
        position = round(available * max(0.0, min(1.0, ratio)))
        if self.orientation() == Qt.Vertical:
            return QRect(rect.left(), rect.top() + position, rect.width(), min(fixed_length, rect.height()))
        return QRect(rect.left() + position, rect.top(), min(fixed_length, rect.width()), rect.height())

    def paintEvent(self, event: QEvent) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        rect = self.rect()
        active = bool(self.property("active"))
        self._draw_track(painter, rect)

        if self.maximum() <= self.minimum():
            return

        handle = self._fixed_handle_rect(rect)
        self._draw_comet(painter, rect, handle)

        # Keep the passive thumb visible in a restrained orange and blend
        # smoothly toward the saturated active orange. Activation is instant;
        # the return to passive is intentionally gradual.
        passive = QColor(156, 83, 31, 150)
        active_color = QColor(255, 132, 34, 248)
        t = max(0.0, min(1.0, self._visual_strength))
        color = QColor(
            round(passive.red() + (active_color.red() - passive.red()) * t),
            round(passive.green() + (active_color.green() - passive.green()) * t),
            round(passive.blue() + (active_color.blue() - passive.blue()) * t),
            round(passive.alpha() + (active_color.alpha() - passive.alpha()) * t),
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(color)
        if self.orientation() == Qt.Vertical:
            half = self.PAINTED_THUMB_THICKNESS / 2.0
            thumb = QRectF(
                rect.center().x() - half,
                handle.top(),
                self.PAINTED_THUMB_THICKNESS,
                handle.height(),
            )
        else:
            half = self.PAINTED_THUMB_THICKNESS / 2.0
            thumb = QRectF(
                handle.left(),
                rect.center().y() - half,
                handle.width(),
                self.PAINTED_THUMB_THICKNESS,
            )
        painter.drawRoundedRect(thumb, 1.0, 1.0)


class FolderNavigationRow(QWidget):
    """One expandable folder row, modeled after T2 Manager's nested buttons."""

    selected = Signal(str)
    expansion_requested = Signal(object, bool)

    def __init__(self, folder: Path, level: int, parent=None) -> None:
        super().__init__(parent)
        self.folder = Path(folder)
        self.level = level
        self._expanded = False
        self._loaded = False
        self._children: list[FolderNavigationRow] = []
        self._has_children = bool(scan_child_folders(self.folder))

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        header = QWidget(self)
        header.setObjectName("folderRowHeader")
        row = QHBoxLayout(header)
        indent = 8 + min(level, 6) * 14
        row.setContentsMargins(indent, 0, 0, 0)
        row.setSpacing(0)
        full_folder_name = display_folder_name(self.folder.name)
        self.button = NavigationRow(
            compact_folder_name(self.folder.name, 2),
            "",
            key=str(self.folder),
            parent=header,
        )
        self.button.setToolTip(full_folder_name)
        self.button.clicked.connect(self._clicked)
        row.addWidget(self.button, 0, Qt.AlignLeft)
        row.addStretch(1)
        header.setMinimumWidth(indent + self.button.width())
        root.addWidget(header)
        self.children_widget = QWidget(self)
        self.children_layout = QVBoxLayout(self.children_widget)
        self.children_layout.setContentsMargins(0, 0, 0, 0)
        self.children_layout.setSpacing(4)
        self.children_widget.hide()
        root.addWidget(self.children_widget)

    def _clicked(self, path: str) -> None:
        self.selected.emit(path)
        if self._has_children:
            self.expansion_requested.emit(self, not self._expanded)

    def ensure_children(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        for folder in scan_child_folders(self.folder):
            child = FolderNavigationRow(folder, self.level + 1, self.children_widget)
            child.selected.connect(self.selected)
            child.expansion_requested.connect(self._handle_child_expansion)
            self._children.append(child)
            self.children_layout.addWidget(child)
        self._equalize_child_button_widths()

    def _equalize_child_button_widths(self) -> None:
        if not self._children:
            return
        group_width = max(child.button._preferred_width for child in self._children)
        for child in self._children:
            child.button.setFixedWidth(group_width)
            indent = 8 + min(child.level, 6) * 14
            child.layout().itemAt(0).widget().setMinimumWidth(indent + group_width)

    def _handle_child_expansion(self, target: object, expanded: bool) -> None:
        if not isinstance(target, FolderNavigationRow):
            return
        if expanded:
            for child in self._children:
                if child is not target:
                    child.collapse_branch()
        target.set_expanded(expanded)

    def collapse_branch(self) -> None:
        for child in self._children:
            child.collapse_branch()
        self.set_expanded(False)

    def set_expanded(self, expanded: bool) -> None:
        if expanded:
            self.ensure_children()
        self._expanded = bool(expanded and self._children)
        self.children_widget.setVisible(self._expanded)

    def set_active_path(self, path: str) -> None:
        active = str(self.folder).casefold() == str(path).casefold()
        self.button.set_active(active)
        for child in self._children:
            child.set_active_path(path)


class FolderPanelFace(QFrame):
    """Scrollable, lazy folder tree for Library and Project panels."""

    row_clicked = Signal(str)

    def __init__(self, *, root_path: Path, subtitle: str, footer: str,
                 parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("flipPanelFace")
        self.root_path = Path(root_path)
        self.root_rows: list[FolderNavigationRow] = []
        layout = QVBoxLayout(self)
        # Keep the left panel itself and the navigation button widths unchanged,
        # but let the scrollbar rail reach the panel's right-side alignment line.
        # The former 20 px outer right margin incorrectly pulled the rail inward.
        layout.setContentsMargins(20, 0, 0, 18)
        layout.setSpacing(0)
        subtitle_label = _label(subtitle, "panelSubtitle")
        subtitle_label.setWordWrap(True)
        layout.addWidget(subtitle_label)
        layout.addSpacing(14)
        scroll = PrecisionScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        vertical_bar = ReactiveScrollBar(
            Qt.Vertical,
            scroll,
            hide_handle_when_idle=True,
            gradient_track=True,
        )
        scroll.setVerticalScrollBar(vertical_bar)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        # Reserve a permanent 40 px safety zone above the horizontal scrollbar.
        # Because this margin belongs to the viewport rather than the end of the
        # content layout, the gap remains visible at every vertical scroll
        # position, not only when the list reaches its final row.
        scroll.setViewportMargins(0, 0, 0, 0)
        # Keep the full-height grayscale rail permanently visible so the left
        # panel balances the thumbnail panel. Only the orange thumb fades out.
        # The visible Library rail is owned by LibraryProjectFlipPanel so it
        # stays fixed while the panel face performs its card-flip animation.
        # Keep this internal bar as the scroll model only.
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll_area = scroll
        self._vertical_scroll_model = vertical_bar
        content = QWidget(scroll)
        content_layout = QVBoxLayout(content)
        self._content_layout = content_layout
        # This trailing margin is updated by CompassWorkspace so the visual
        # distance from the Library content to its rail mirrors the distance
        # from the thumbnail rail to the Asset Inspector content.
        content_layout.setContentsMargins(0, 0, 24, 0)
        content_layout.setSpacing(4)
        folders = scan_child_folders(self.root_path)
        if folders:
            for folder in folders:
                row = FolderNavigationRow(folder, 0, content)
                row.selected.connect(self._select_path)
                row.expansion_requested.connect(self._handle_root_expansion)
                self.root_rows.append(row)
                content_layout.addWidget(row)
            self._equalize_root_button_widths()
        else:
            missing = _label(f"Folder not found: {self.root_path}", "panelSubtitle")
            missing.setWordWrap(True)
            content_layout.addWidget(missing)
        content_layout.addStretch(1)
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        layout.addWidget(_label(footer, "panelFooter"))

    def _equalize_root_button_widths(self) -> None:
        if not self.root_rows:
            return
        group_width = max(row.button._preferred_width for row in self.root_rows)
        for row in self.root_rows:
            row.button.setFixedWidth(group_width)
            header = row.layout().itemAt(0).widget()
            header.setMinimumWidth(8 + group_width)

    def vertical_scroll_model(self) -> ReactiveScrollBar:
        return self._vertical_scroll_model

    def set_trailing_alignment_margin(self, margin: int) -> None:
        left, top, _right, bottom = self._content_layout.getContentsMargins()
        self._content_layout.setContentsMargins(
            left, top, max(0, int(margin)), bottom
        )

    def _handle_root_expansion(self, target: object, expanded: bool) -> None:
        if not isinstance(target, FolderNavigationRow):
            return
        if expanded:
            for row in self.root_rows:
                if row is not target:
                    row.collapse_branch()
        target.set_expanded(expanded)

    def _select_path(self, path: str) -> None:
        for row in self.root_rows:
            row.set_active_path(path)
        self.row_clicked.emit(path)


class LibraryProjectFlipPanel(QFrame):
    """Left navigation panel with Library, Project and AI faces."""

    face_changed = Signal(str)
    library_requested = Signal(str)
    project_requested = Signal(str)
    ai_requested = Signal(str)
    plan3d_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("leftFlipPanel")
        self.setMinimumSize(190, 250)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.setCursor(Qt.ArrowCursor)
        self._tabs = LibraryProjectTabs(self)
        self._tabs.mode_requested.connect(self._request_mode)

        self.library_face = FolderPanelFace(
            root_path=LIBRARY_ROOT,
            subtitle="Assets, materials and references",
            footer="Choose Library, Project or AI above",
            parent=self,
        )
        self.library_face.setObjectName("libraryFace")
        self.library_face.row_clicked.connect(self.library_requested)

        self.projects_face = FolderPanelFace(
            root_path=PROJECT_ROOT,
            subtitle="Active work and production spaces",
            footer="Choose Library, Project or AI above",
            parent=self,
        )
        self.projects_face.setObjectName("projectsFace")
        self.projects_face.row_clicked.connect(self.project_requested)
        self.projects_face.hide()

        self.ai_face = PanelFace(
            eyebrow="COMPASS / 03",
            title="AI",
            subtitle="AI-assisted asset and project tools",
            rows=(
                ("AI Generate", "READY"),
                ("AI Enhance", "NEW"),
                ("AI Analyze", "BETA"),
                ("AI Assistant", "LIVE"),
            ),
            footer="Choose Library, Project or AI above",
            parent=self,
        )
        self.ai_face.setObjectName("aiFace")
        self.ai_face.row_clicked.connect(self.ai_requested)
        self.ai_face.hide()

        self.plan3d_face = Plan3DMenuFace(parent=self)
        self.plan3d_face.setObjectName("plan3dFace")
        self.plan3d_face.command_requested.connect(self.plan3d_requested)
        self.plan3d_face.hide()

        # Fixed edge rail: visually identical to the former face-owned rail,
        # but parented to the non-rotating panel shell. The gray line and the
        # orange thumb therefore remain stationary during Library/Project flips.
        self._edge_scrollbar = ReactiveScrollBar(
            Qt.Vertical,
            self,
            hide_handle_when_idle=True,
            gradient_track=True,
        )
        self._edge_scrollbar.valueChanged.connect(
            self._apply_edge_scroll_value
        )
        for face in (self.library_face, self.projects_face):
            model = face.vertical_scroll_model()
            model.rangeChanged.connect(self._sync_edge_scrollbar)
            model.valueChanged.connect(self._sync_edge_scrollbar)

        self._angle = 0.0
        self._current_mode = "library"
        self._selected_asset_path = ""
        self._preview_worker = None
        self._pending_mode: str | None = None
        self._hovered = False
        self._motion_enabled = True

        self._flip_animation = QPropertyAnimation(self, b"flipAngle", self)
        self._flip_animation.setDuration(640)
        self._flip_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._flip_animation.finished.connect(self._finish_flip)


    def set_edge_alignment(self, panel_gap: int) -> None:
        # Mirror the right-hand geometry exactly:
        # center scrollbar (5 px) + workspace gap + Inspector inner margin.
        # The Library content lives before its own 5 px scrollbar, therefore
        # subtract that scrollbar width from the mirrored distance.
        inspector_inner_margin = 20
        scrollbar_width = ReactiveScrollBar.INTERACTION_THICKNESS
        library_scrollbar_clearance = 17
        trailing_margin = max(
            0,
            int(panel_gap)
            + inspector_inner_margin
            - scrollbar_width
            + library_scrollbar_clearance,
        )
        self.library_face.set_trailing_alignment_margin(trailing_margin)
        self.projects_face.set_trailing_alignment_margin(trailing_margin)

    def _active_scroll_model(self) -> ReactiveScrollBar | None:
        mode = self._pending_mode or self._current_mode
        if mode == "library":
            return self.library_face.vertical_scroll_model()
        if mode == "project":
            return self.projects_face.vertical_scroll_model()
        return None

    def _apply_edge_scroll_value(self, value: int) -> None:
        model = self._active_scroll_model()
        if model is not None and model.value() != value:
            model.setValue(value)

    def _sync_edge_scrollbar(self, *_args) -> None:
        model = self._active_scroll_model()
        if model is None:
            self._edge_scrollbar.hide()
            return
        self._edge_scrollbar.show()
        previous_value = self._edge_scrollbar.value()
        self._edge_scrollbar.blockSignals(True)
        self._edge_scrollbar.setRange(model.minimum(), model.maximum())
        self._edge_scrollbar.setPageStep(model.pageStep())
        self._edge_scrollbar.setSingleStep(model.singleStep())
        self._edge_scrollbar.setValue(model.value())
        self._edge_scrollbar.blockSignals(False)
        if self._edge_scrollbar.value() != previous_value:
            self._edge_scrollbar.passive_activity()
        self._edge_scrollbar.raise_()

    def get_flip_angle(self) -> float:
        return self._angle

    def set_flip_angle(self, angle: float) -> None:
        self._angle = float(angle)
        self._layout_active_face()
        self.update()

    flipAngle = Property(float, get_flip_angle, set_flip_angle)

    @property
    def showing_projects(self) -> bool:
        return (self._pending_mode or self._current_mode) == "project"

    def flip(self) -> None:
        self._request_mode(
            "library" if self.showing_projects else "project"
        )

    def mouseReleaseEvent(self, event) -> None:
        # Library/Project navigation is intentionally owned only by the
        # dedicated tab control. Empty panel space must never flip the face.
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self._hovered = True
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hovered = False
        super().leaveEvent(event)

    def resizeEvent(self, event) -> None:
        self._layout_active_face()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

    def _layout_active_face(self) -> None:
        if self.width() <= 0 or self.height() <= 0:
            return

        visible_mode = (
            self._pending_mode
            if self._pending_mode is not None and self._angle >= 90.0
            else self._current_mode
        )
        faces = {
            "library": self.library_face,
            "project": self.projects_face,
            "ai": self.ai_face,
            "plan3d": self.plan3d_face,
        }
        visible_face = faces[visible_mode]
        for mode, face in faces.items():
            if mode != visible_mode:
                face.hide()
        visible_face.show()

        scale = max(0.025, abs(math.cos(math.radians(self._angle))))
        inset = 8
        # Keep the left edge and panel dimensions unchanged, but extend the
        # active Library/Project face to the panel's right edge. This moves
        # only the vertical scrollbar 8 px to the right; row/button widths are
        # compensated inside FolderPanelFace and remain unchanged.
        full_rect = self.rect().adjusted(inset, inset, 0, -inset)
        self._tabs.setGeometry(8, 18, max(1, self.width() - 16), 43)
        full_rect.adjust(0, 65, 0, 0)
        face_width = max(1, round(full_rect.width() * scale))
        face_height_loss = round((1.0 - scale) * 16)
        face_height = max(1, full_rect.height() - face_height_loss)
        face_x = full_rect.center().x() - (face_width // 2)
        face_y = full_rect.center().y() - (face_height // 2)
        visible_face.setGeometry(face_x, face_y, face_width, face_height)

        # Keep the rail on the panel shell, not inside the transforming face.
        # Its x-position is the stable left alignment line seen beside the
        # thumbnail area; only the content behind it performs the flip.
        rail_top = full_rect.top() + 40
        rail_bottom = full_rect.bottom() - 24
        self._edge_scrollbar.setGeometry(
            max(0, self.width() - self._edge_scrollbar.width()),
            max(0, rail_top),
            self._edge_scrollbar.width(),
            max(1, rail_bottom - rail_top),
        )
        self._sync_edge_scrollbar()

    def _finish_flip(self) -> None:
        if self._pending_mode is not None:
            self._current_mode = self._pending_mode
        self._pending_mode = None
        self._angle = 0.0
        self._layout_active_face()
        self.face_changed.emit(self._current_mode)
        self._sync_edge_scrollbar()
        self.update()

    def select_mode(self, mode: str) -> None:
        self._request_mode(mode)

    def _request_mode(self, mode: str) -> None:
        if mode not in {"library", "project", "ai", "plan3d"}:
            return
        if self._flip_animation.state() == QAbstractAnimation.Running:
            return
        if mode == self._current_mode:
            return
        self._pending_mode = mode
        self._tabs.set_mode(mode)
        self._angle = 0.0
        self._flip_animation.setStartValue(0.0)
        self._flip_animation.setEndValue(180.0)
        self._flip_animation.start()
        self._sync_edge_scrollbar()

    def set_motion_enabled(self, enabled: bool) -> None:
        self._motion_enabled = bool(enabled)
        if self._motion_enabled:
            if self._flip_animation.state() == QAbstractAnimation.Paused:
                self._flip_animation.resume()
        elif self._flip_animation.state() == QAbstractAnimation.Running:
            self._flip_animation.pause()
        self.update()


THUMBNAIL_MANAGER = ThumbnailManager()


class ThumbnailArtwork(QWidget):
    """Lightweight, code-native preview used by the functional test Library."""

    def __init__(self, seed: int, asset_path: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._seed = seed
        thumbnail_path = THUMBNAIL_MANAGER.find_thumbnail(asset_path, 240, 138)
        self._thumbnail_cache_key = f"compass-thumb:{thumbnail_path}" if thumbnail_path else ""
        cached_pixmap = QPixmap()
        if self._thumbnail_cache_key:
            cached_pixmap = QPixmapCache.find(self._thumbnail_cache_key) or QPixmap()
        if cached_pixmap.isNull() and thumbnail_path:
            cached_pixmap = QPixmap(str(thumbnail_path))
            if not cached_pixmap.isNull():
                QPixmapCache.insert(self._thumbnail_cache_key, cached_pixmap)
        self._thumbnail = cached_pixmap
        self._scaled_cache: dict[tuple[int, int], QPixmap] = {}
        self.setMinimumHeight(64)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        bounds = QRectF(self.rect()).adjusted(1.0, 1.0, -1.0, -1.0)
        if not self._thumbnail.isNull():
            target_size = (max(1, int(bounds.width())), max(1, int(bounds.height())))
            scaled = self._scaled_cache.get(target_size)
            if scaled is None:
                scaled = self._thumbnail.scaled(
                    target_size[0], target_size[1], Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self._scaled_cache[target_size] = scaled
            target = QRectF(
                bounds.center().x() - scaled.width() / 2,
                bounds.center().y() - scaled.height() / 2,
                scaled.width(),
                scaled.height(),
            )
            painter.drawPixmap(target.toRect(), scaled)
            return

        surface = QLinearGradient(bounds.topLeft(), bounds.bottomRight())
        base = 26 + ((self._seed * 7) % 18)
        surface.setColorAt(0.0, QColor(base + 22, base + 22, base + 22, 215))
        surface.setColorAt(0.55, QColor(base, base, base, 185))
        surface.setColorAt(1.0, QColor(8, 8, 8, 145))
        painter.setPen(Qt.NoPen)
        painter.setBrush(surface)
        painter.drawRoundedRect(bounds, 9, 9)

        center = bounds.center()
        span = min(bounds.width(), bounds.height())
        object_rect = QRectF(
            center.x() - (span * 0.34),
            center.y() - (span * 0.19),
            span * 0.68,
            span * 0.38,
        )
        painter.setPen(QPen(QColor(203, 203, 203, 112), 1.15))
        painter.setBrush(QColor(145, 145, 145, 31))
        painter.drawRoundedRect(object_rect, 7, 7)

        horizon = object_rect.bottom() + 8
        painter.setPen(QPen(QColor(220, 220, 220, 42), 1.0))
        painter.drawLine(
            QPointF(bounds.left() + 14, horizon),
            QPointF(bounds.right() - 14, horizon),
        )

        offset = ((self._seed % 5) - 2) * span * 0.025
        painter.setPen(QPen(QColor(238, 238, 238, 92), 1.0))
        painter.drawArc(
            object_rect.adjusted(9 + offset, -9, -9 + offset, 9),
            24 * 16,
            132 * 16,
        )


class AssetThumbnailCard(QFrame):
    """Clickable thumbnail card that owns its selected state."""

    clicked = Signal(str, str, str, str)

    def __init__(
        self,
        name: str,
        asset_type: str,
        asset_format: str,
        seed: int,
        *,
        asset_path: str = "",
        interactive: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("assetThumbnailCard")
        self.setProperty("selected", False)
        self._interactive = bool(interactive)
        self.setProperty("interactive", self._interactive)
        self.setCursor(
            Qt.PointingHandCursor if self._interactive else Qt.ArrowCursor
        )
        self.setMinimumSize(76, 76)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.name = name
        self.asset_type = asset_type
        self.asset_format = asset_format
        self.asset_path = asset_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 7)
        layout.setSpacing(5)
        layout.addWidget(ThumbnailArtwork(seed, asset_path, self), 1)
        self._title_label = _label(name, "thumbnailTitle")
        self._meta_label = _label(
            f"{asset_type}  ·  {asset_format}",
            "thumbnailMeta",
        )
        layout.addWidget(self._title_label)
        layout.addWidget(self._meta_label)

    def resizeEvent(self, event) -> None:
        available = max(1, event.size().width() - 16)
        self._title_label.setText(
            QFontMetrics(self._title_label.font()).elidedText(
                self.name,
                Qt.ElideRight,
                available,
            )
        )
        self._meta_label.setText(
            QFontMetrics(self._meta_label.font()).elidedText(
                f"{self.asset_type}  ·  {self.asset_format}",
                Qt.ElideRight,
                available,
            )
        )
        super().resizeEvent(event)

    @property
    def is_selected(self) -> bool:
        return bool(self.property("selected"))

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", bool(selected))
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if self._interactive and event.button() == Qt.LeftButton and self.rect().contains(
            event.position().toPoint()
        ):
            self.clicked.emit(self.name, self.asset_type, self.asset_format, self.asset_path)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ThumbnailBrowser(QWidget):
    """The active center-page opened by clicking a Library category."""

    asset_selected = Signal(str, str, str, str)
    DESKTOP_COLUMNS = 5
    GRID_GAP = 12

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("thumbnailBrowser")
        self.current_category = ""
        self.cards: list[AssetThumbnailCard] = []
        self._column_count = 0
        self._card_side = 0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._scroll = PrecisionScrollArea(self)
        self._scroll.setObjectName("thumbnailScroll")
        self._scroll.setFrameShape(QFrame.NoFrame)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        thumbnail_vertical_bar = ReactiveScrollBar(
            Qt.Vertical,
            self._scroll,
            hide_handle_when_idle=True,
            gradient_track=True,
        )
        self._scroll.setVerticalScrollBar(thumbnail_vertical_bar)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self._scroll.setAttribute(Qt.WA_StyledBackground, False)

        self._canvas = QWidget(self._scroll)
        self._canvas.setObjectName("thumbnailViewport")
        self._canvas.setAttribute(Qt.WA_StyledBackground, False)
        self._grid = QGridLayout(self._canvas)
        self._grid.setContentsMargins(2, 2, 10, 14)
        self._grid.setHorizontalSpacing(self.GRID_GAP)
        self._grid.setVerticalSpacing(self.GRID_GAP)
        self._grid.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self._scroll.setWidget(self._canvas)
        layout.addWidget(self._scroll)

        self.set_category(next(iter(ASSET_CATALOG), ""))

    def set_catalog_key(self, category: str, catalog: dict[str, tuple[tuple[str, str, str, str], ...]]) -> None:
        global ASSET_CATALOG
        ASSET_CATALOG = catalog
        self.set_category(category)

    def set_category(self, category: str) -> None:
        if category not in ASSET_CATALOG:
            category = next(iter(ASSET_CATALOG), "")
        self.current_category = category

        while self._grid.count():
            item = self._grid.takeAt(0)
            old_card = item.widget()
            if old_card is not None:
                # deleteLater() alone leaves the old card visible until Qt
                # flushes deferred deletes. When a category opens during the
                # first reveal, that produces a second ghost grid beneath the
                # new 50 cards. Remove it from the scene immediately.
                old_card.hide()
                old_card.setParent(None)
                old_card.deleteLater()
        self.cards = []

        category_parts = {display_folder_name(part).casefold() for part in Path(category).parts}
        texture_mode = bool(category_parts.intersection({"texture", "textures"}))
        visible_assets = tuple(
            asset
            for asset in ASSET_CATALOG.get(category, ())
            if (
                THUMBNAIL_MANAGER.is_image(asset[3])
                if texture_mode
                else THUMBNAIL_MANAGER.is_01_image(asset[3])
            )
        )
        for seed, (name, asset_type, asset_format, asset_path) in enumerate(
            visible_assets,
            start=1,
        ):
            card = AssetThumbnailCard(
                name,
                asset_type,
                asset_format,
                seed,
                asset_path=asset_path,
                interactive=True,
                parent=self._canvas,
            )
            card.clicked.connect(self._select_asset)
            self.cards.append(card)

        self._column_count = 0
        self._card_side = 0
        self._reflow_cards()

    def resizeEvent(self, event) -> None:
        self._reflow_cards()
        super().resizeEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        # The browser is populated while hidden. Recalculate after QStackedWidget
        # has assigned the real viewport width so startup never keeps tiny cards.
        self._column_count = 0
        QTimer.singleShot(0, self.refresh_layout)

    def refresh_layout(self) -> None:
        self._column_count = 0
        self._card_side = 0
        self._reflow_cards()

    def _reflow_cards(self) -> None:
        available = max(1, self._scroll.viewport().width() - 12)
        columns = self.DESKTOP_COLUMNS
        gaps = self.GRID_GAP * max(0, columns - 1)
        card_side = max(56, min(150, (available - gaps) // columns))
        if (
            columns == self._column_count
            and card_side == self._card_side
            and self._grid.count() == len(self.cards)
        ):
            return
        self._column_count = columns
        self._card_side = card_side
        while self._grid.count():
            self._grid.takeAt(0)
        for index, card in enumerate(self.cards):
            card.setFixedSize(card_side, card_side)
            self._grid.addWidget(card, index // columns, index % columns)
        rows = math.ceil(len(self.cards) / columns)
        self._canvas.setMinimumHeight(
            max(1, (rows * card_side) + (max(0, rows - 1) * self.GRID_GAP) + 16)
        )

    def _select_asset(
        self,
        name: str,
        asset_type: str,
        asset_format: str,
        asset_path: str,
    ) -> None:
        for card in self.cards:
            card.set_selected(card.asset_path == asset_path)
        self.asset_selected.emit(name, asset_type, asset_format, asset_path)


class PreviewCanvas(QWidget):
    """Active workspace labels drawn over the persistent orbit backdrop."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("previewCanvas")
        self.setMinimumHeight(220)
        self._phase = 0.0
        self._asset_name = ""
        self._asset_meta = ""
        self._asset_pixmap = QPixmap()
        self._asset_source = ""
        self._timer = QTimer(self)
        self._timer.setInterval(24)
        self._timer.timeout.connect(self._advance)
        self._timer.start()

    def _advance(self) -> None:
        self._phase = (self._phase + 0.006) % 1.0
        self.update()

    def set_motion_enabled(self, enabled: bool) -> None:
        if enabled:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def set_asset(self, name: str, asset_type: str, asset_format: str, asset_path: str = "") -> None:
        self._asset_name = name
        self._asset_meta = f"{asset_type} · {asset_format}"
        self._asset_source = asset_path
        thumb = THUMBNAIL_MANAGER.find_thumbnail(asset_path, 960, 540) if asset_path else None
        self._asset_pixmap = QPixmap(str(thumb)) if thumb else QPixmap()
        self._phase = 0.0
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        bounds = QRectF(self.rect()).adjusted(2, 2, -2, -2)
        if not self._asset_pixmap.isNull():
            target = bounds.adjusted(12, 12, -12, -48)
            scaled = self._asset_pixmap.scaled(
                target.size().toSize(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
            x = target.left() + (target.width() - scaled.width()) / 2.0
            y = target.top() + (target.height() - scaled.height()) / 2.0
            painter.drawPixmap(round(x), round(y), scaled)

        if self._asset_name:
            painter.setPen(QColor(225, 225, 225, 210))
            font = painter.font()
            font.setPointSizeF(13.0)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            painter.drawText(
                bounds.adjusted(0, 0, 0, -24),
                Qt.AlignHCenter | Qt.AlignBottom,
                self._asset_name,
            )
            painter.setPen(QColor(122, 152, 185, 190))
            font.setPointSizeF(9.0)
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            painter.drawText(
                bounds,
                Qt.AlignHCenter | Qt.AlignBottom,
                self._asset_meta,
            )


class AssetPreviewDetailPanel(QFrame):
    """Scrollable horizontal asset metadata panel below panels 7 and 9."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("assetPreviewDetailPanel")
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(18, 8, 6, 8)
        outer_layout.setSpacing(0)

        scroll = PrecisionScrollArea(self)
        scroll.setObjectName("assetDetailScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        detail_bar = ReactiveScrollBar(
            Qt.Vertical,
            scroll,
            hide_handle_when_idle=False,
            gradient_track=True,
        )
        scroll.setVerticalScrollBar(detail_bar)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)

        fields = QFrame(scroll)
        fields.setObjectName("assetDetailFields")
        grid = QGridLayout(fields)
        grid.setContentsMargins(0, 10, 12, 10)
        grid.setHorizontalSpacing(22)
        grid.setVerticalSpacing(12)
        self._values: dict[str, QLabel] = {}
        entries = (("File Name", "No selection"), ("File Type", "-"), ("Format", "-"), ("Preview", "Panel 9"))
        for index, (key, value) in enumerate(entries):
            column = (index % 2) * 2
            row = index // 2
            grid.addWidget(_label(key, "inspectorKey"), row, column)
            value_label = _label(value, "inspectorValue")
            self._values[key] = value_label
            grid.addWidget(value_label, row, column + 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        grid.setRowStretch(2, 1)
        scroll.setWidget(fields)
        outer_layout.addWidget(scroll, 1)

    def set_asset(self, name: str, asset_type: str, asset_format: str, asset_path: str = "") -> None:
        del asset_path
        self._values["File Name"].setText(name)
        self._values["File Type"].setText(asset_type)
        self._values["Format"].setText(asset_format)
        self._values["Preview"].setText("Panel 9")


class Plan3DEyeButton(QToolButton):
    """Layer visibility control drawn at the display's native resolution."""

    def __init__(self, visible: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plan3dEyeButton")
        self.setCheckable(True)
        self.setChecked(visible)
        self.setFixedSize(25, 22)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor("#e0e0e0" if self.isChecked() else "#858585")
        painter.setPen(QPen(color, 1.35))
        painter.setBrush(Qt.NoBrush)
        width, height = self.width(), self.height()
        outline = QPainterPath()
        outline.moveTo(4.5, height / 2)
        outline.cubicTo(8, 5.5, width - 8, 5.5, width - 4.5, height / 2)
        outline.cubicTo(width - 8, height - 5.5, 8, height - 5.5, 4.5, height / 2)
        painter.drawPath(outline)
        painter.setBrush(color if self.isChecked() else Qt.NoBrush)
        painter.drawEllipse(QRectF(width / 2 - 2.7, height / 2 - 2.7, 5.4, 5.4))


class Plan3DPanelButton(QToolButton):
    """Compact close and refresh icons for the tool-panel headers."""

    def __init__(self, symbol: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.symbol = symbol
        self.setObjectName("plan3dHeaderButton")
        self.setFixedSize(27, 26)
        self.setCursor(Qt.PointingHandCursor)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor("#f39743" if self.underMouse() else "#d2d2d2")
        painter.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        if self.symbol == "close":
            painter.drawLine(QPointF(9, 9), QPointF(18, 17))
            painter.drawLine(QPointF(18, 9), QPointF(9, 17))
        elif self.symbol == "refresh":
            arc = QPainterPath()
            arc.moveTo(18.5, 10)
            arc.cubicTo(16.8, 6.5, 11.8, 6.2, 9, 9)
            arc.cubicTo(5.5, 12.5, 8.4, 18.7, 13.5, 19)
            arc.cubicTo(16.1, 19.1, 18.2, 17.3, 19.2, 15.3)
            painter.drawPath(arc)
            painter.drawLine(QPointF(18.5, 10), QPointF(18.4, 5.9))
            painter.drawLine(QPointF(18.5, 10), QPointF(14.6, 9.4))


class Plan3DLayerRow(QFrame):
    """Compact eye, semantic swatch and assignment control."""

    def __init__(self, name: str, semantic: str = "Unassigned",
                 visible: bool = True, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("plan3dLayerRow")
        self.setFixedHeight(28)
        row = QHBoxLayout(self)
        row.setContentsMargins(4, 1, 4, 1)
        row.setSpacing(6)
        self.eye = Plan3DEyeButton(visible, self)
        row.addWidget(self.eye)
        self.swatch = QFrame(self)
        self.swatch.setFixedSize(6, 20)
        row.addWidget(self.swatch)
        name_label = QLabel(name, self)
        self.name_label = name_label
        name_label.setObjectName("plan3dLayerName")
        name_label.setMinimumWidth(0)
        row.addWidget(name_label, 1)
        self.semantic = QComboBox(self)
        self.semantic.setObjectName("plan3dSemantic")
        self.semantic.addItems(("Wall", "Exterior Wall", "Facade", "Window", "Door",
                                "Sliding Door", "Stair", "Detail", "Furniture", "Roof",
                                "Unassigned"))
        self.semantic.setCurrentText(semantic if semantic in
                                     [self.semantic.itemText(i) for i in range(self.semantic.count())]
                                     else "Unassigned")
        self.semantic.setMinimumWidth(86)
        self.semantic.setMaximumWidth(112)
        self.semantic.currentTextChanged.connect(self._update_swatch)
        self._update_swatch(self.semantic.currentText())
        row.addWidget(self.semantic)

    def _update_swatch(self, semantic: str) -> None:
        color = {"Wall": "#518fff", "Exterior Wall": "#aeb2b6",
                 "Facade": "#315b85", "Window": "#ffb866", "Door": "#64c790",
                 "Sliding Door": "#348367", "Stair": "#ffe18b",
                 "Detail": "#edb7d2", "Furniture": "#c7af59",
                 "Roof": "#ec7075"}.get(semantic, "#d6d6d6")
        self.swatch.setStyleSheet("background-color: " + color + ";")


class Plan3DToolPanel(QFrame):
    """Compact Plan3D-inspired panel with fixed header and scrollable content."""

    closed = Signal(str)

    def __init__(self, title: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title = title
        self.setObjectName("plan3dToolPanel")
        self.setStyleSheet("""
            QFrame#plan3dToolPanel { background: #151515; border: 1px solid #383838; border-radius: 8px; }
            QFrame#plan3dToolHeader { background: #1b1b1b; border: none;
                                      border-bottom: 1px solid #383838; border-top-left-radius: 8px; border-top-right-radius: 8px; }
            QLabel#plan3dPanelTitle { background: transparent; color: #d0d0d0; font-size: 11px;
                                       font-weight: 600; border: none; }
            QLabel#plan3dLayerName { background: transparent; color: #f1f1f1; font-size: 10px; border: none; }
            QLabel#plan3dFieldName { background: transparent; color: #a6a6a6; font-size: 10px; border: none; }
            QLabel#plan3dFieldValue { background: transparent; color: #eeeeee; font-size: 10px; border: none; }
            QFrame#plan3dLayerRow { background: #202020; border: none;
                                     border-bottom: 1px solid #383838; border-radius: 4px; }
            QToolButton#plan3dHeaderButton { background: transparent;
                border: none; border-radius: 5px; padding: 0; }
            QToolButton#plan3dHeaderButton:hover { background: #3b3b3b; }
            QToolButton#plan3dEyeButton { background: transparent;
                border: none; border-radius: 5px; padding: 0; }
            QToolButton#plan3dEyeButton:hover { background: #3b3b3b; }
            QToolButton#plan3dEyeButton:checked { background: #303030; }
            QComboBox#plan3dSemantic { color: #f5f5f5; background: #202020;
                border: 1px solid #383838; border-radius: 4px; padding: 2px 5px; font-size: 10px; }
            QComboBox#plan3dSemantic QAbstractItemView { background: #202020;
                color: #eeeeee; selection-background-color: #404040; }
            QScrollArea { border: none; background: #151515; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        header = QFrame(self)
        header.setObjectName("plan3dToolHeader")
        header.setFixedHeight(28)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 0, 0)
        header_layout.setSpacing(2)
        label = QLabel(title, header)
        label.setObjectName("plan3dPanelTitle")
        label.setAttribute(Qt.WA_TranslucentBackground, True)
        header_layout.addWidget(label)
        header_layout.addStretch(1)
        if title == "Layers":
            refresh = Plan3DPanelButton("refresh", header)
            refresh.setToolTip("Refresh layers")
            refresh.clicked.connect(self.refresh_layers)
            header_layout.addWidget(refresh)
        close_button = Plan3DPanelButton("close", header)
        close_button.setToolTip("Close " + title)
        close_button.clicked.connect(lambda: self.closed.emit(self.title))
        header_layout.addWidget(close_button)
        layout.addWidget(header)
        self.content = PrecisionScrollArea(self)
        self.content.setWidgetResizable(True)
        self.content.setFrameShape(QFrame.NoFrame)
        self.content.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scrollbar = ReactiveScrollBar(
            Qt.Vertical, self.content,
            hide_handle_when_idle=True, gradient_track=True,
        )
        self.content.setVerticalScrollBar(scrollbar)
        self.content.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.body = QWidget(self.content)
        self.body_layout = QVBoxLayout(self.body)
        self.body_layout.setContentsMargins(4, 5, 4, 5)
        self.body_layout.setSpacing(3)
        self.body_layout.addStretch(1)
        self.layer_rows = []
        self.content.setWidget(self.body)
        layout.addWidget(self.content, 1)

    def set_layers(self, layers: list[tuple[str, str, bool]]) -> None:
        if self.title != "Layers":
            return
        self._clear_body()
        self.layer_rows = []
        for name, semantic, visible in layers:
            row = Plan3DLayerRow(name, semantic, visible, self.body)
            self.layer_rows.append(row)
            self.body_layout.addWidget(row)
            row.eye.toggled.connect(self._layer_changed)
            row.semantic.currentTextChanged.connect(self._layer_changed)
        self.body_layout.addStretch(1)

    def refresh_layers(self) -> None:
        strip = self.parent()
        if isinstance(strip, Plan3DToolStrip):
            self.set_layers(list(strip.layer_state))

    def _layer_changed(self, *_args) -> None:
        strip = self.parent()
        if isinstance(strip, Plan3DToolStrip):
            strip.layer_state = [(row.name_label.text(), row.semantic.currentText(),
                                  row.eye.isChecked()) for row in self.layer_rows]
            if strip.layer_edited is not None:
                strip.layer_edited("Layer setting changed")

    def set_fields(self, fields: list[tuple[str, str]]) -> None:
        if self.title == "Layers":
            return
        self._clear_body()
        for name, value in fields:
            item = QFrame(self.body)
            item.setStyleSheet("background: #1b1b1b; border: none;")
            fields_layout = QVBoxLayout(item)
            fields_layout.setContentsMargins(6, 3, 6, 3)
            fields_layout.setSpacing(1)
            label = QLabel(name, item)
            label.setObjectName("plan3dFieldName")
            fields_layout.addWidget(label)
            field_value = QLabel(value, item)
            field_value.setObjectName("plan3dFieldValue")
            field_value.setWordWrap(True)
            fields_layout.addWidget(field_value)
            self.body_layout.addWidget(item)
        self.body_layout.addStretch(1)

    def _clear_body(self) -> None:
        while self.body_layout.count():
            item = self.body_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()



class ProjectDetailsPanel(Plan3DToolPanel):
    """Viewport assignments and per-floor dimensions used by the Plan3D engine."""

    FACADES = ("Front", "Rear", "Right", "Left")
    FLOOR_NAMES = (
        "Basement 3", "Basement 2", "Basement 1", "Ground Floor",
        "First Floor", "Second Floor", "Third Floor", "Fourth Floor",
        "Fifth Floor", "Sixth Floor", "Seventh Floor", "Eighth Floor",
        "Ninth Floor", "Tenth Floor", "Roof Floor",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Project Details", parent)
        self._clear_body()
        self._viewport = None
        self._assignments = {"facades": {}, "floor_plans": {}}
        self._floor_settings = {}
        self._floor_pivots = {}
        self._analysis_results = {}
        self._active_floor_name = "Ground Floor"
        self._pending_selection = None
        self._confirmed = False
        self._restoring = False

        title = QLabel("VIEWPORT SELECTION", self.body)
        title.setObjectName("plan3dPanelTitle")
        self.body_layout.addWidget(title)

        tabs = QWidget(self.body)
        tabs_layout = QHBoxLayout(tabs)
        tabs_layout.setContentsMargins(0, 0, 0, 0)
        tabs_layout.setSpacing(5)
        self.facade_tab = QPushButton("Facade", tabs)
        self.floor_tab = QPushButton("Floor Plan", tabs)
        for tab in (self.facade_tab, self.floor_tab):
            tab.setObjectName("projectDetailsTab")
            tab.setCheckable(True)
            tabs_layout.addWidget(tab, 1)
        self.facade_tab.clicked.connect(lambda: self._show_section("facade"))
        self.floor_tab.clicked.connect(lambda: self._show_section("floor"))
        self.body_layout.addWidget(tabs)

        self.facade_group = QWidget(self.body)
        facade_layout = QVBoxLayout(self.facade_group)
        facade_layout.setContentsMargins(0, 5, 0, 0)
        facade_layout.setSpacing(6)
        facade_row = QWidget(self.facade_group)
        facade_row_layout = QHBoxLayout(facade_row)
        facade_row_layout.setContentsMargins(0, 0, 0, 0)
        facade_row_layout.setSpacing(5)
        self.select_facade = QPushButton("Select in Viewport", facade_row)
        self.facade_name = QComboBox(facade_row)
        self.facade_name.addItems(self.FACADES)
        facade_row_layout.addWidget(self.select_facade, 2)
        facade_row_layout.addWidget(self.facade_name, 1)
        facade_layout.addWidget(facade_row)
        self.facade_analysis = QPushButton("Facade Analysis", self.facade_group)
        self.floor_areas = QPushButton("Show Floor Areas", self.facade_group)
        self.add_pivot = QPushButton("Add Pivot", self.facade_group)
        for button in (self.facade_analysis, self.floor_areas, self.add_pivot):
            facade_layout.addWidget(button)
        self.body_layout.addWidget(self.facade_group)

        self.floor_group = QWidget(self.body)
        floor_layout = QVBoxLayout(self.floor_group)
        floor_layout.setContentsMargins(0, 5, 0, 0)
        floor_layout.setSpacing(6)
        floor_row = QWidget(self.floor_group)
        floor_row_layout = QHBoxLayout(floor_row)
        floor_row_layout.setContentsMargins(0, 0, 0, 0)
        floor_row_layout.setSpacing(5)
        self.select_floor = QPushButton("Select Floor", floor_row)
        self.floor_name = QComboBox(floor_row)
        self.floor_name.setEditable(True)
        self.floor_name.addItems(self.FLOOR_NAMES)
        self.floor_name.setCurrentText("Ground Floor")
        floor_row_layout.addWidget(self.select_floor, 2)
        floor_row_layout.addWidget(self.floor_name, 1)
        floor_layout.addWidget(floor_row)
        self.dimensions = {}
        for label, key in (("Floor Elevation", "floor_elevation_cm"),
                           ("Wall Height", "wall_height_cm"),
                           ("Interior Door Height", "door_height_cm")):
            field_label = QLabel(label + " (cm)", self.floor_group)
            field_label.setObjectName("plan3dFieldName")
            entry = QLineEdit(self.floor_group)
            entry.setObjectName("projectDetailsMeasure")
            entry.setPlaceholderText("Enter cm")
            entry.setValidator(QDoubleValidator(-100000.0, 100000.0, 2, entry))
            entry.textChanged.connect(self._dimensions_changed)
            floor_layout.addWidget(field_label)
            floor_layout.addWidget(entry)
            self.dimensions[key] = entry
        self.body_layout.addWidget(self.floor_group)

        self.selection_status = QLabel("Select facade and floor plan areas in Drawing Area.", self.body)
        self.selection_status.setObjectName("plan3dFieldName")
        self.selection_status.setWordWrap(True)
        self.body_layout.addWidget(self.selection_status)
        self.body_layout.addStretch(1)

        footer = QWidget(self)
        footer.setObjectName("projectDetailsFooter")
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(8, 8, 8, 8)
        footer_layout.setSpacing(6)
        divider = QFrame(footer)
        divider.setFrameShape(QFrame.HLine)
        divider.setObjectName("projectDetailsDivider")
        footer_layout.addWidget(divider)
        self.confirm_button = QPushButton("Details Confirmed", footer)
        self.create_button = QPushButton("Create 3D Model", footer)
        footer_layout.addWidget(self.confirm_button)
        footer_layout.addWidget(self.create_button)
        self.layout().addWidget(footer)

        self.setStyleSheet(self.styleSheet() + """
            QPushButton#projectDetailsTab, QWidget#projectDetailsFooter QPushButton,
            QWidget#plan3dToolPanel QPushButton {
                background: #252525; border: 1px solid #464646;
                border-radius: 6px; color: #ececec; padding: 5px;
            }
            QPushButton#projectDetailsTab:hover, QWidget#plan3dToolPanel QPushButton:hover {
                border-color: #f39743; background: #333333;
            }
            QPushButton#projectDetailsTab:checked { background: #424242; border-color: #777777; }
            QPushButton:disabled { color: #777777; background: #202020; border-color: #333333; }
            QLineEdit#projectDetailsMeasure, QWidget#plan3dToolPanel QComboBox {
                background: #202020; color: #eeeeee; border: 1px solid #484848;
                border-radius: 5px; padding: 4px;
            }
            QFrame#projectDetailsDivider { color: #555555; background: #555555; max-height: 1px; }
        """)
        self.select_facade.clicked.connect(lambda: self._start_selection("facades"))
        self.select_floor.clicked.connect(lambda: self._start_selection("floor_plans"))
        self.facade_analysis.clicked.connect(self.run_facade_analysis)
        self.floor_areas.clicked.connect(self.show_floor_areas)
        self.add_pivot.clicked.connect(self.add_floor_pivot)
        self.floor_name.currentTextChanged.connect(self._floor_changed)
        self.confirm_button.clicked.connect(self.confirm_details)
        self.create_button.clicked.connect(self.create_model)
        self._show_section("facade")
        self._update_buttons()

    def _show_section(self, section: str) -> None:
        facade = section == "facade"
        self.facade_tab.setChecked(facade)
        self.floor_tab.setChecked(not facade)
        self.facade_group.setVisible(facade)
        self.floor_group.setVisible(not facade)

    def attach_viewport(self, viewport) -> None:
        if viewport is self._viewport:
            return
        if self._viewport is not None:
            try:
                self._viewport.assignmentRegionSelected.disconnect(self._selection_finished)
                self._viewport.floorPivotCommitted.disconnect(self._pivot_finished)
            except (RuntimeError, TypeError):
                pass
        self._viewport = viewport
        if viewport is not None:
            viewport.assignmentRegionSelected.connect(self._selection_finished)
            viewport.floorPivotCommitted.connect(self._pivot_finished)
            viewport.set_floor_pivot_records(self._floor_pivots)
            viewport.show_assignment_regions(self._assignments)
        self._update_buttons()

    def _start_selection(self, kind: str) -> None:
        if self._viewport is None:
            self.selection_status.setText("Open a drawing before selecting an area.")
            return
        name = self.facade_name.currentText() if kind == "facades" else self.floor_name.currentText().strip()
        if not name:
            self.selection_status.setText("Choose a facade or enter a floor name.")
            return
        self._pending_selection = (kind, name)
        self._viewport.begin_assignment_selection(kind, name)
        self.selection_status.setText("Drag a rectangle around " + name + " in Drawing Area.")

    def _selection_finished(self, kind, name, rect) -> None:
        pending = self._pending_selection
        if not pending or kind != pending[0] or len(rect) != 4:
            return
        group, selected_name = pending
        self._pending_selection = None
        self._assignments[group][selected_name] = list(rect)
        self._confirmed = False
        self._analysis_results.clear()
        self._viewport.show_assignment_regions(self._assignments)
        self.selection_status.setText(selected_name + " selected.")
        self._update_buttons()

    def _floor_changed(self, name: str) -> None:
        if self._restoring:
            return
        self._active_floor_name = name.strip()
        settings = self._floor_settings.get(self._active_floor_name, {})
        self._restoring = True
        for key, widget in self.dimensions.items():
            value = settings.get(key)
            widget.setText("" if value is None else str(value))
        self._restoring = False
        self._update_buttons()

    def _dimensions_changed(self, *_args) -> None:
        if self._restoring:
            return
        name = self.floor_name.currentText().strip()
        if not name:
            return
        values = {}
        for key, widget in self.dimensions.items():
            try:
                values[key] = float(widget.text())
            except ValueError:
                break
        if len(values) == len(self.dimensions) and all(math.isfinite(v) for v in values.values()):
            self._floor_settings[name] = values
        else:
            self._floor_settings.pop(name, None)
        self._confirmed = False
        self._analysis_results.clear()
        self._update_buttons()

    def add_floor_pivot(self) -> None:
        name = self.floor_name.currentText().strip()
        rect = self._assignments["floor_plans"].get(name)
        if self._viewport is None or rect is None:
            self.selection_status.setText("Select a floor plan area before adding its pivot.")
            return
        self._viewport.begin_floor_pivot_selection(name, rect, self._floor_pivots.get(name))
        self.selection_status.setText("Choose the pivot point for " + name + " in Drawing Area.")

    def _pivot_finished(self, floor_name, x, y, snap_kind) -> None:
        if floor_name not in self._assignments["floor_plans"]:
            return
        self._floor_pivots[floor_name] = {
            "floor_name": floor_name, "pivot_x": float(x), "pivot_y": float(y),
            "snap_kind": str(snap_kind), "master": floor_name == "Ground Floor",
        }
        self._viewport.set_floor_pivot_records(self._floor_pivots)
        self._confirmed = False
        self._update_buttons()
        self.selection_status.setText(floor_name + " pivot set.")

    def _ready(self) -> bool:
        floors = self._assignments["floor_plans"]
        return bool(
            self._viewport is not None
            and all(name in self._assignments["facades"] for name in self.FACADES)
            and floors
            and all(name in self._floor_pivots and name in self._floor_settings
                    and self._floor_settings[name].get("floor_elevation_cm") is not None
                    and self._floor_settings[name].get("wall_height_cm", 0) > 0
                    and self._floor_settings[name].get("door_height_cm", 0) > 0
                    for name in floors)
        )

    def _update_buttons(self) -> None:
        floor = self.floor_name.currentText().strip()
        self.add_pivot.setEnabled(self._viewport is not None and floor in self._assignments["floor_plans"])
        self.confirm_button.setEnabled(self._ready() and not self._confirmed)
        self.create_button.setEnabled(self._ready() and self._confirmed)

    def run_facade_analysis(self) -> None:
        try:
            from artmach_compass.plan3d_backend import analyze_facade_windows
            if self._viewport is None or not self._assignments["facades"]:
                raise ValueError("Select facade areas first.")
            if not self._floor_settings:
                raise ValueError("Enter the dimensions for the selected floors first.")
            analysis = analyze_facade_windows(
                self._viewport, self._assignments["facades"], self._floor_settings,
            )
            self._analysis_results["facade_windows_all_floors"] = analysis
            self._viewport.show_facade_height_reference_lines(
                [entry["datum_line"] for entry in analysis.values()]
            )
            count = sum(len(entry["windows"]) for entry in analysis.values())
            self.selection_status.setText(f"Facade Analysis: {count} windows measured.")
        except Exception as exc:
            self.selection_status.setText(str(exc))

    def show_floor_areas(self) -> None:
        try:
            from artmach_compass.plan3d_backend import analyze_floor_areas
            report = analyze_floor_areas(self)
            count = len(report.get("floors", {}))
            self.selection_status.setText(f"Show Floor Areas: {count} floors processed.")
        except Exception as exc:
            self.selection_status.setText(str(exc))

    def confirm_details(self) -> None:
        if not self._ready():
            return
        self._confirmed = True
        self._update_buttons()
        self.selection_status.setText("Project details confirmed.")

    def create_model(self) -> None:
        if not self._confirmed or not self._ready():
            return
        try:
            from artmach_compass.plan3d_backend import prepare_max_transfer
            result = prepare_max_transfer(self)
            pending = result.get("pending_script") or result.get("pending_path")
            self.selection_status.setText("3D model prepared for 3ds Max: " + str(pending))
        except Exception as exc:
            self.selection_status.setText(str(exc))

    def values(self) -> dict:
        return {
            "floor_name": self.floor_name.currentText().strip(),
            "floor_settings": deepcopy(self._floor_settings),
            "assignments": deepcopy(self._assignments),
            "analysis": deepcopy(self._analysis_results),
            "confirmed": self._confirmed,
            "pivots": {"version": 2, "coordinate_space": "cad_source_xy",
                       "records": deepcopy(self._floor_pivots)},
        }

    def load_data(self, data: dict) -> None:
        self._assignments = deepcopy(data.get("assignments", {"facades": {}, "floor_plans": {}}))
        self._assignments.setdefault("facades", {})
        self._assignments.setdefault("floor_plans", {})
        self._floor_settings = deepcopy(data.get("floor_settings", {}))
        self._floor_pivots = deepcopy(data.get("pivots", {}).get("records", {}))
        self._analysis_results = deepcopy(data.get("analysis", {}))
        self._confirmed = bool(data.get("confirmed", False))
        floor = str(data.get("floor_name") or "Ground Floor")
        self.floor_name.setCurrentText(floor)
        self._floor_changed(floor)
        if self._viewport is not None:
            self._viewport.set_floor_pivot_records(self._floor_pivots)
            self._viewport.show_assignment_regions(self._assignments)
        self._update_buttons()


class Plan3DToolStrip(QFrame):
    """Open panels stay in canonical order and share available width."""

    panels_changed = Signal(bool)

    ORDER = ("Layers", "Properties", "Project Details")
    # Temporary UI examples. Replace with actual DWG layer data when connected.
    DEMO_LAYERS = (
        ("KP Duvarlar", "Wall", True),
        ("KP Dış Duvar", "Exterior Wall", True),
        ("C Arka", "Facade", True),
        ("C Sağ", "Facade", True),
        ("C Sol", "Facade", True),
        ("C Ön", "Facade", True),
        ("C Pencereler", "Window", True),
        ("KP pencereler", "Window", True),
        ("C Dış Kapılar", "Door", True),
        ("KP Dış Kapılar", "Door", True),
        ("KP İç Kapılar", "Door", True),
        ("C Sliding Doors", "Sliding Door", True),
        ("KP Sliding Doors", "Sliding Door", True),
        ("KP Merdiven", "Stair", True),
        ("KP Detay", "Detail", True),
        ("KP Mobilyalar", "Furniture", True),
        ("KP Çatı", "Roof", True),
        ("KP Çatı Pencereler", "Roof", True),
        ("0", "Unassigned", False),
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("assetPreviewDetailPanel")
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)
        self._panels: dict[str, Plan3DToolPanel] = {}
        self.layer_state = list(self.DEMO_LAYERS)
        self.layer_edited = None
        self.project_details_state = {}
        self.viewport = None

    def open_panel(self, title: str) -> None:
        if title not in self.ORDER:
            return
        if title in self._panels:
            self._panels[title].show()
            self._panels[title].raise_()
            self.updateGeometry()
            self.panels_changed.emit(True)
            return
        panel = ProjectDetailsPanel(self) if title == "Project Details" else Plan3DToolPanel(title, self)
        if title == "Layers":
            panel.set_layers(list(self.layer_state))
        elif title == "Project Details":
            panel.attach_viewport(self.viewport)
            if self.project_details_state:
                panel.load_data(self.project_details_state)
        panel.closed.connect(self.close_panel)
        self._panels[title] = panel
        index = sum(name in self._panels for name in self.ORDER[:self.ORDER.index(title)])
        self._layout.insertWidget(index, panel, 1)
        panel.show()
        self.updateGeometry()
        self.panels_changed.emit(True)

    def close_panel(self, title: str) -> None:
        panel = self._panels.pop(title, None)
        if panel is not None:
            if title == "Layers":
                self.layer_state = [(row.name_label.text(), row.semantic.currentText(),
                                     row.eye.isChecked()) for row in panel.layer_rows]
            elif title == "Project Details":
                self.project_details_state = panel.values()
                panel.attach_viewport(None)
            self._layout.removeWidget(panel)
            panel.hide()
            panel.deleteLater()
            self.updateGeometry()
            self.panels_changed.emit(bool(self._panels))


class CenterWorkspacePanel(QFrame):
    """Center composition: 7 and 9 equal on top, 8 spanning below."""

    intro_finished = Signal()
    asset_selected = Signal(str, str, str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("animatedCenterPanel")
        self.setMinimumSize(520, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(7, 8, 8, 8)
        layout.setSpacing(8)

        top_row = QWidget(self)
        self._top_row = top_row
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(8)

        self._thumbnail_frame = QFrame(top_row)
        self._thumbnail_frame.setObjectName("centerSubPanel")
        thumbnail_layout = QVBoxLayout(self._thumbnail_frame)
        self._drawing_layout = thumbnail_layout
        thumbnail_layout.setContentsMargins(10, 10, 10, 10)
        thumbnail_layout.setSpacing(8)
        self._drawing_heading = _label("THUMBNAILS / ASSET CARDS", "panelEyebrow")
        self._drawing_heading.setStyleSheet("font-size: 12pt;")
        self._drawing_heading.setFixedHeight(22)
        self._drawing_heading.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        thumbnail_layout.addWidget(self._drawing_heading, 0, Qt.AlignTop)
        self._thumbnail_browser = ThumbnailBrowser(self._thumbnail_frame)
        self._thumbnail_browser.asset_selected.connect(self._open_asset_preview)
        thumbnail_layout.addWidget(self._thumbnail_browser, 1)
        self._active_plan3d_viewport = None

        self._viewer_frame = QFrame(top_row)
        self._viewer_frame.setObjectName("centerSubPanel")
        viewer_layout = QVBoxLayout(self._viewer_frame)
        viewer_layout.setContentsMargins(10, 10, 10, 10)
        viewer_layout.setSpacing(8)
        viewer_heading = _label("MAIN 3D VIEWER / WORKSPACE", "panelEyebrow")
        viewer_heading.setStyleSheet("font-size: 12pt;")
        viewer_layout.addWidget(viewer_heading)
        # Two pages: a flat 2D thumbnail fallback (no matching GLB yet) and the
        # real interactive 3D viewport (GLB preview available). Previously this
        # panel only ever showed the JPEG thumbnail, even after a GLB existed.
        self._viewer_stack = QStackedWidget(self._viewer_frame)
        self._preview_canvas = PreviewCanvas(self._viewer_frame)
        self._model_viewer = Model3DViewer(self._viewer_frame)
        self._viewer_stack.addWidget(self._preview_canvas)
        self._viewer_stack.addWidget(self._model_viewer)
        self._model_viewer.model_loaded.connect(self._on_model_loaded)
        self._model_viewer.model_failed.connect(self._on_model_failed)
        viewer_layout.addWidget(self._viewer_stack, 1)

        self._preview_status = _label("Select a thumbnail linked to a .MAX asset", "previewGenerationStatus")
        self._preview_status.setWordWrap(True)
        viewer_layout.addWidget(self._preview_status)

        self._preview_progress = QProgressBar(self._viewer_frame)
        self._preview_progress.setObjectName("previewGenerationProgress")
        self._preview_progress.setRange(0, 100)
        self._preview_progress.setValue(0)
        self._preview_progress.setTextVisible(False)
        self._preview_progress.setFixedHeight(5)
        self._preview_progress.hide()
        viewer_layout.addWidget(self._preview_progress)

        self._generate_preview_button = QPushButton("GENERATE PREVIEW", self._viewer_frame)
        self._generate_preview_button.setObjectName("generatePreviewButton")
        self._generate_preview_button.setEnabled(False)
        self._generate_preview_button.clicked.connect(self._generate_preview)
        viewer_layout.addWidget(self._generate_preview_button)

        top_layout.addWidget(self._thumbnail_frame, 1)
        top_layout.addWidget(self._viewer_frame, 1)

        self._detail_panel = AssetPreviewDetailPanel(self)
        layout.addWidget(top_row, 3)
        layout.addWidget(self._detail_panel, 2)
        self._plan3d_tools = Plan3DToolStrip(self)
        layout.addWidget(self._plan3d_tools, 2)
        self._plan3d_tools.panels_changed.connect(self._update_plan3d_tool_visibility)
        self._plan3d_tools.hide()
        self._ai_placeholder = QFrame(self)
        self._ai_placeholder.setObjectName("centerSubPanel")
        placeholder_layout = QVBoxLayout(self._ai_placeholder)
        placeholder_label = QLabel("Under Development", self._ai_placeholder)
        placeholder_label.setAlignment(Qt.AlignCenter)
        placeholder_label.setStyleSheet("color: #c7ced1; font-size: 18pt; font-weight: 500;")
        placeholder_layout.addWidget(placeholder_label, 1)
        layout.addWidget(self._ai_placeholder, 1)
        self._ai_placeholder.hide()
        self._current_mode = "library"
        self._selected_thumbnail_path = ""
        self._resolved_max_path = ""
        self._preview_worker = None

    @property
    def current_mode(self) -> str:
        return self._current_mode

    @property
    def thumbnail_browser(self) -> ThumbnailBrowser:
        return self._thumbnail_browser

    def set_workspace_mode(self, mode: str) -> None:
        plan3d = mode == "plan3d"
        self._top_row.setVisible(mode != "ai")
        self._ai_placeholder.setVisible(mode == "ai")
        self._viewer_frame.setVisible(mode not in ("plan3d", "ai"))
        self._thumbnail_browser.setVisible(not plan3d)
        if self._active_plan3d_viewport is not None:
            self._active_plan3d_viewport.setVisible(plan3d)
        self._drawing_heading.setText("DRAWING AREA" if plan3d else "THUMBNAILS / ASSET CARDS")
        self._thumbnail_frame.setStyleSheet(
            "QFrame#centerSubPanel { background-color: #151515; "
            "border: 1px solid #383838; border-radius: 9px; }"
            if plan3d else ""
        )
        self._detail_panel.setVisible(mode not in ("plan3d", "ai"))
        self._current_mode = mode
        self._update_plan3d_tool_visibility()
        if plan3d:
            QTimer.singleShot(0, self._thumbnail_browser.refresh_layout)

    def _update_plan3d_tool_visibility(self, *_args) -> None:
        visible = self._current_mode == "plan3d" and bool(self._plan3d_tools._panels)
        self._plan3d_tools.setMinimumHeight(180 if visible else 0)
        self._plan3d_tools.setVisible(visible)
        if visible:
            for panel in self._plan3d_tools._panels.values():
                panel.show()
            self._plan3d_tools.updateGeometry()
        self.layout().activate()

    def new_plan3d_project(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "New Project — Select CAD Drawing",
            str(Path.home() / "Desktop"),
            "CAD Drawings (*.dwg *.dxf);;DWG (*.dwg);;DXF (*.dxf)",
        )
        if not path:
            return
        viewport = None
        try:
            viewport = create_embedded_plan3d_viewport(self._thumbnail_frame)
            viewport.load_file(path)
        except Exception as exc:
            if viewport is not None:
                viewport.deleteLater()
            self._show_plan3d_warning(str(exc))
            return
        previous = self._active_plan3d_viewport
        if previous is not None:
            self._drawing_layout.removeWidget(previous)
            previous.hide()
        self._active_plan3d_viewport = viewport
        self._drawing_layout.addWidget(viewport, 1)
        self._plan3d_tools.viewport = viewport
        self._plan3d_tools.project_details_state = {}
        details = self._plan3d_tools._panels.get("Project Details")
        if details is not None:
            details.load_data({})
            details.attach_viewport(viewport)
        try:
            self._plan3d_tools.layer_state = [
                (name, viewport.get_layer_type(name), viewport.is_layer_selected(name))
                for name in viewport.get_layer_names()
            ]
            layers_panel = self._plan3d_tools._panels.get("Layers")
            if layers_panel is not None:
                layers_panel.set_layers(self._plan3d_tools.layer_state)
        except AttributeError:
            pass
        self.set_workspace_mode("plan3d")

    def _show_plan3d_warning(self, message: str) -> None:
        if "pywin32" in message:
            message = (
                "DWG support requires pywin32 in the Python environment running Compass.\n"
                "Install it with: py -3.11 -m pip install pywin32"
            )
        dialog = QMessageBox(self)
        dialog.setWindowTitle("Plan3D")
        dialog.setIcon(QMessageBox.Warning)
        dialog.setText(message)
        dialog.setStandardButtons(QMessageBox.Ok)
        dialog.setStyleSheet(
            "QMessageBox { background: #181818; color: #e9e9e9; "
            "border: 1px solid #404040; } "
            "QLabel { color: #e9e9e9; font-size: 12px; min-width: 290px; } "
            "QPushButton { background: #2b2b2b; color: #e9e9e9; "
            "border: 1px solid #515151; border-radius: 6px; "
            "padding: 6px 15px; min-width: 64px; } "
            "QPushButton:hover { background: #3e3e3e; border-color: #ef8c31; }"
        )
        dialog.exec()

    def open_plan3d_project(self) -> None:
        project_file, _ = QFileDialog.getOpenFileName(
            self, "Open Plan3D Project",
            str(Path.home() / "Desktop" / "Plan3D"),
            "Plan3D Project (*.p3d)",
        )
        if not project_file:
            return
        viewport = None
        try:
            project_path = Path(project_file)
            data = json.loads(project_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict) or data.get("format") != "MAP_PLAN3D":
                raise ValueError("This is not a Plan3D project file.")

            source_data = data.get("source") or {}
            if not isinstance(source_data, dict):
                raise ValueError("The project source is invalid.")
            cad_value = (source_data.get("cad")
                         or source_data.get("managed_dwg")
                         or source_data.get("original_path"))
            if not cad_value:
                raise ValueError("No CAD path was found in this project file.")
            cad_path = Path(str(cad_value)).expanduser()
            if not cad_path.is_absolute():
                cad_path = project_path.parent / cad_path
            if not cad_path.is_file():
                raise FileNotFoundError(f"CAD file was not found: {cad_path}")

            viewport = create_embedded_plan3d_viewport(self._thumbnail_frame)
            viewport.load_file(str(cad_path))
            if viewport.scene() is None or not viewport.scene().items():
                raise ValueError("The CAD file contains no drawable geometry.")

            saved_layers = data.get("layers") or {}
            if not isinstance(saved_layers, dict):
                saved_layers = {}
            current_names = list(viewport.get_layer_names())
            for name in current_names:
                saved = saved_layers.get(name) or {}
                if not isinstance(saved, dict):
                    saved = {}
                viewport.set_layer_type(name, saved.get("type", "Unassigned"))
                viewport.set_layer_selected(name, bool(saved.get("visible", True)))

            saved_order = data.get("layer_order") or []
            ordered = [name for name in saved_order if name in current_names]
            ordered.extend(name for name in current_names if name not in ordered)
            layers = [
                (name, viewport.get_layer_type(name),
                 viewport.is_layer_selected(name))
                for name in ordered
            ]
            view_state = data.get("viewport") or {}
        except Exception as exc:
            if viewport is not None:
                viewport.deleteLater()
            self._show_plan3d_warning(str(exc))
            return

        previous = self._active_plan3d_viewport
        if previous is not None:
            self._drawing_layout.removeWidget(previous)
            previous.hide()
            previous.deleteLater()
        self._active_plan3d_viewport = viewport
        self._drawing_layout.addWidget(viewport, 1)
        self._plan3d_tools.viewport = viewport
        self._plan3d_tools.project_details_state = data.get("export_details") or {}
        details = self._plan3d_tools._panels.get("Project Details")
        if details is not None:
            details.attach_viewport(viewport)
            details.load_data(self._plan3d_tools.project_details_state)
        self._plan3d_tools.layer_state = layers
        if "Layers" in self._plan3d_tools._panels:
            self._plan3d_tools._panels["Layers"].set_layers(layers)
        self.set_workspace_mode("plan3d")
        QTimer.singleShot(
            0, lambda view=viewport, state=view_state:
            self._restore_plan3d_view(view, state)
        )

    def _restore_plan3d_view(self, viewport, state) -> None:
        if viewport is not self._active_plan3d_viewport or not isinstance(state, dict):
            return
        try:
            transform = QTransform(*[
                float(state[key]) for key in
                ("m11", "m12", "m13", "m21", "m22", "m23",
                 "m31", "m32", "m33")
            ])
            viewport.setTransform(transform)
            viewport.centerOn(float(state["center_x"]), float(state["center_y"]))
            viewport._user_has_interacted = True
        except (KeyError, TypeError, ValueError):
            pass

    def open_plan3d_tool(self, tool: str) -> None:
        if tool in Plan3DToolStrip.ORDER:
            self.set_workspace_mode("plan3d")
            self._plan3d_tools.open_panel(tool)
            panel = self._plan3d_tools._panels.get(tool)
            if panel is not None and tool == "Properties":
                viewport = self._active_plan3d_viewport
                drawing = Path(str(getattr(viewport, "_source_path", "") or "")) if viewport is not None else None
                panel.set_fields([
                    ("Drawing", drawing.name if drawing and drawing.name else "No drawing open"),
                    ("Layers", str(len(viewport.get_layer_names())) if viewport is not None else "0"),
                    ("Format", drawing.suffix.upper().lstrip(".") if drawing and drawing.suffix else "—"),
                ])
            self._update_plan3d_tool_visibility()
            self._plan3d_tools.raise_()
            self.layout().activate()
            QTimer.singleShot(0, self._update_plan3d_tool_visibility)

    def activate_library(self, category: str) -> None:
        self.set_workspace_mode("library")
        category_path = Path(category)
        key = str(category_path)
        if category_path.is_dir() and key not in ASSET_CATALOG:
            assets = scan_category_assets(category_path)
            ASSET_CATALOG[key] = tuple((asset.name, asset.asset_type, asset.asset_format, asset.path) for asset in assets)
        self._thumbnail_browser.set_catalog_key(key, ASSET_CATALOG)
        self._current_mode = "library"
        QTimer.singleShot(0, self._thumbnail_browser.refresh_layout)

    def activate_project(self, project: str) -> None:
        self.set_workspace_mode("project")
        project_path = Path(project)
        self._preview_canvas.set_asset(display_folder_name(project_path.name) if project_path.name else "Project", "Project", "READY")
        self._viewer_stack.setCurrentWidget(self._preview_canvas)
        self._current_mode = "project"

    def activate_plan3d(self, tool: str) -> None:
        self.set_workspace_mode("plan3d")
        self.open_plan3d_tool(tool)

    def activate_ai(self, tool: str) -> None:
        self.set_workspace_mode("ai")

    def _open_asset_preview(self, name: str, asset_type: str, asset_format: str, asset_path: str = "") -> None:
        self._detail_panel.set_asset(name, asset_type, asset_format, asset_path)
        self._current_mode = "asset_preview"
        self._selected_thumbnail_path = asset_path
        resolved_max = resolve_max_for_thumbnail(asset_path)
        self._resolved_max_path = str(resolved_max) if resolved_max else ""
        can_generate = resolved_max is not None
        self._generate_preview_button.setEnabled(can_generate)
        get_logger().info(
            "Asset selected: name=%r path=%r resolved_max=%r", name, asset_path, self._resolved_max_path
        )

        output = resolved_max.with_name(resolved_max.stem + "_preview.glb") if resolved_max is not None else None
        if output is not None and output.is_file():
            # A GLB preview already exists for this asset - show the real 3D
            # model instead of the flat thumbnail image.
            self._model_viewer.load_model(str(output))
            self._viewer_stack.setCurrentWidget(self._model_viewer)
            self._preview_status.setText("Preview exists for matching MAX")
        else:
            self._preview_canvas.set_asset(name, asset_type, asset_format, asset_path)
            self._viewer_stack.setCurrentWidget(self._preview_canvas)
            if resolved_max is not None:
                self._preview_status.setText(f"Matching MAX ready: {resolved_max.name}")
            elif THUMBNAIL_MANAGER.is_image(asset_path):
                self._preview_status.setText("No unambiguous matching .MAX file was found for this thumbnail")
            else:
                self._preview_status.setText("Select a thumbnail image linked to a .MAX asset")
        self.asset_selected.emit(name, asset_type, asset_format, asset_path)

    def _on_model_loaded(self, glb_path: str) -> None:
        get_logger().info("3D viewer: model loaded successfully: %s", glb_path)

    def _on_model_failed(self, glb_path: str) -> None:
        get_logger().error("3D viewer: failed to display model: %s", glb_path)
        self._preview_status.setText(
            "3D viewer could not display this GLB - click 'Log' in the top bar to see the "
            "exact reason (file: %LOCALAPPDATA%\\ArtmachCompass\\logs\\compass.log)."
        )

    def _generate_preview(self) -> None:
        source = Path(self._resolved_max_path)
        get_logger().info("GENERATE PREVIEW clicked for %s", source)
        if source.suffix.casefold() != ".max" or not source.is_file():
            get_logger().error("GENERATE PREVIEW aborted: no valid .MAX file at %s", source)
            self._preview_status.setText("The displayed thumbnail has no valid matching .MAX file")
            return
        if self._preview_worker is not None and self._preview_worker.isRunning():
            get_logger().warning("GENERATE PREVIEW ignored: a conversion is already running")
            return
        self._generate_preview_button.setEnabled(False)
        self._generate_preview_button.setText("GENERATING...")
        self._preview_progress.setValue(2)
        self._preview_progress.show()
        self._preview_status.setText("Starting background conversion...")
        worker = PreviewGenerationThread(str(source), self)
        self._preview_worker = worker
        worker.stage_changed.connect(self._on_preview_stage)
        worker.succeeded.connect(self._on_preview_success)
        worker.failed.connect(self._on_preview_failure)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def _on_preview_stage(self, message: str, progress: int) -> None:
        get_logger().info("Preview generation stage (%s%%): %s", progress, message)
        self._preview_status.setText(message)
        self._preview_progress.setValue(progress)

    def _on_preview_success(self, output_path: str, report: dict) -> None:
        validation = report.get("validation") or {}
        meshes = validation.get("meshes", 0)
        materials = validation.get("materials", 0)
        images = validation.get("images", 0)
        get_logger().info(
            "Preview generation succeeded: %s (meshes=%s materials=%s images=%s)",
            output_path, meshes, materials, images,
        )
        self._preview_progress.setValue(100)
        self._preview_status.setText(
            f"Preview ready · {meshes} mesh · {materials} materials · {images} images"
        )
        self._generate_preview_button.setText("REGENERATE PREVIEW")
        self._generate_preview_button.setEnabled(True)
        self._detail_panel._values["Preview"].setText(Path(output_path).name)
        # Switch the viewer over to the freshly generated model right away,
        # instead of leaving the flat thumbnail showing.
        self._model_viewer.load_model(output_path)
        self._viewer_stack.setCurrentWidget(self._model_viewer)

    def _on_preview_failure(self, message: str, diagnostics_path: str = "") -> None:
        get_logger().error(
            "Preview generation failed: %s (diagnostics=%s)", message, diagnostics_path or "none"
        )
        self._preview_progress.setValue(0)
        self._viewer_stack.setCurrentWidget(self._preview_canvas)
        if diagnostics_path:
            path = Path(diagnostics_path)
            self._preview_status.setText(
                f"Preview failed · Diagnostic ZIP created: {path.name}"
            )
            if path.parent.is_dir():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))
        else:
            self._preview_status.setText(f"Preview failed: {message}")
        self._generate_preview_button.setText("RETRY PREVIEW")
        self._generate_preview_button.setEnabled(True)

    def play_intro(self, *, fast: bool = False, start_opacity: float = 0.0) -> None:
        self.update()


class InspectorPanel(QFrame):
    """Right-side asset metadata and activity panel."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("rightInspectorPanel")
        self.setMinimumSize(190, 250)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 21, 20, 18)
        layout.setSpacing(0)

        layout.addWidget(_label("CONTEXT / 03", "panelEyebrow"))
        layout.addSpacing(7)
        layout.addWidget(_label("Asset Inspector", "panelHeading"))
        layout.addSpacing(5)
        layout.addWidget(_label("Selection and activity details", "panelSubtitle"))
        layout.addSpacing(23)

        self._values: dict[str, QLabel] = {}
        for key, value in (
            ("Selection", "Audi R8"),
            ("Type", "3D Model"),
            ("Format", "GLB"),
            ("Status", "Ready"),
        ):
            field = QFrame(self)
            field.setObjectName("inspectorField")
            field_row = QHBoxLayout(field)
            field_row.setContentsMargins(11, 8, 11, 8)
            field_row.addWidget(_label(key, "inspectorKey"))
            field_row.addStretch(1)
            value_label = _label(value, "inspectorValue")
            self._values[key] = value_label
            field_row.addWidget(value_label)
            layout.addWidget(field)
            layout.addSpacing(6)

        layout.addSpacing(15)
        layout.addWidget(_label("LOCAL CACHE", "inspectorKey"))
        layout.addSpacing(7)
        cache = QProgressBar(self)
        cache.setObjectName("cacheProgress")
        cache.setRange(0, 100)
        cache.setValue(72)
        cache.setTextVisible(False)
        cache.setFixedHeight(5)
        layout.addWidget(cache)
        layout.addStretch(1)

        activity = QFrame(self)
        activity.setObjectName("activityCard")
        activity_layout = QVBoxLayout(activity)
        activity_layout.setContentsMargins(12, 10, 12, 10)
        activity_layout.setSpacing(4)
        activity_layout.addWidget(_label("ACTIVITY", "inspectorKey"))
        self._activity = _label("Preview renderer is ready", "activityText")
        activity_layout.addWidget(self._activity)
        layout.addWidget(activity)

    @property
    def current_selection(self) -> str:
        return self._values["Selection"].text()

    def set_selection(
        self,
        name: str,
        asset_type: str,
        asset_format: str,
        asset_path: str = "",
    ) -> None:
        self._values["Selection"].setText(name)
        self._values["Type"].setText(asset_type)
        self._values["Format"].setText(asset_format)
        self._values["Status"].setText("Selected")
        preview = Path(asset_path).with_name(Path(asset_path).stem + "_preview.glb") if asset_path else None
        self._activity.setText(
            "GLB preview is ready" if preview and preview.is_file() else f"{name} is active"
        )


class Plan3DHistoryField(QLineEdit):
    history_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._plan3d = False
        self.undo_button = QToolButton(self)
        self.redo_button = QToolButton(self)
        for button, symbol, tip in (
            (self.undo_button, "↶", "Undo"),
            (self.redo_button, "↷", "Redo"),
        ):
            button.setText(symbol)
            button.setToolTip(tip)
            button.setCursor(Qt.PointingHandCursor)
            button.setFixedSize(34, 32)
            button.setStyleSheet(
                "QToolButton { color: #e0e7e9; background: #292929; "
                "border: 1px solid #484848; border-radius: 6px; "
                "font-family: 'Segoe UI Symbol'; font-size: 20px; font-weight: 600; } "
                "QToolButton:hover { color: #ff922f; background: #383838; } "
                "QToolButton:disabled { color: #818181; background: #202020; }"
            )
            button.hide()

    def set_plan3d(self, enabled: bool) -> None:
        self._plan3d = enabled
        self.setReadOnly(enabled)
        self.setClearButtonEnabled(not enabled)
        self.setPlaceholderText("History" if enabled else "Search assets...")
        self.setText("")
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.IBeamCursor)
        self.setTextMargins(9, 0, 79 if enabled else 0, 0)
        self.undo_button.setVisible(enabled)
        self.redo_button.setVisible(enabled)
        self._position_buttons()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._position_buttons()

    def _position_buttons(self) -> None:
        y = (self.height() - 32) // 2
        self.undo_button.move(self.width() - 74, y)
        self.redo_button.move(self.width() - 38, y)

    def mouseReleaseEvent(self, event) -> None:
        if self._plan3d and event.button() == Qt.LeftButton:
            self.history_requested.emit()
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class TopCommandBar(QFrame):
    """Compact production-style command bar inspired by the approved layout."""

    mode_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("topCommandBar")
        self.setFixedHeight(62)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 8, 14, 8)
        layout.setSpacing(8)

        brand = QFrame(self)
        brand.setObjectName("brandBlock")
        brand.setFixedWidth(380)
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 4, 10, 4)
        brand_layout.setSpacing(4)
        logo = QLabel(brand)
        logo.setObjectName("compassBrandLogo")
        logo.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        logo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        resource_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
        logo_pixmap = QPixmap(str(resource_root / "resources" / "icons" / "ArtmachCompass.png"))
        if not logo_pixmap.isNull():
            logo.setPixmap(logo_pixmap.scaled(42, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        logo.setFixedSize(42, 42)
        brand_layout.addWidget(logo, 0, Qt.AlignLeft | Qt.AlignVCenter)
        manager_label = QLabel("T2 MANAGER", brand)
        manager_label.setStyleSheet(
            "color: #dedede; font-size: 13pt; font-weight: 600; "
            "letter-spacing: 1px; background: transparent;"
        )
        brand_layout.addWidget(manager_label, 0, Qt.AlignVCenter)
        brand_layout.addStretch(1)
        version_label = _label("v0.6.1", "brandVersion")
        version_label.setAlignment(Qt.AlignLeft | Qt.AlignBottom)
        version_label.setFixedHeight(18)
        brand_layout.addWidget(version_label, 0, Qt.AlignLeft | Qt.AlignBottom)
        layout.addWidget(brand)

        self.mode_buttons = {}
        for text, subtitle, active in (
            ("LIBRARY", "Library", True),
            ("PROJECTS", "Projects", False),
            ("PLAN3D", "CAD to 3D", False),
            ("AI", "Artificial Intelligence", False),
        ):
            button = QPushButton(text, self)
            button.setObjectName("topModeButton")
            button_font = button.font()
            button_font.setPointSize(max(10, button_font.pointSize()) + 2)
            button.setFont(button_font)
            button.setProperty("active", active)
            button.setCheckable(True)
            button.setChecked(active)
            button.setFixedSize(118, 46)
            button.clicked.connect(lambda _checked=False, mode=text: self.mode_requested.emit(mode))
            self.mode_buttons[text] = button
            layout.addWidget(button)

        layout.addSpacing(18)
        self.search = Plan3DHistoryField(self)
        self.search.setObjectName("globalSearch")
        self.search.setPlaceholderText("Search assets...")
        self.search.setClearButtonEnabled(True)
        self.undo_button = self.search.undo_button
        self.redo_button = self.search.redo_button
        self.search.setMinimumWidth(260)
        self.search.setMaximumWidth(520)
        self.search.setFixedHeight(40)
        layout.addWidget(self.search, 1)
        layout.addSpacing(14)

        for text in ("Upload", "Download", "Sync", "Log", "Settings"):
            button = QToolButton(self)
            button.setObjectName("commandButton")
            button.setText(text)
            button.setToolButtonStyle(Qt.ToolButtonTextOnly)
            button.setFixedHeight(36)
            if text == "Log":
                button.setToolTip("Open the diagnostic log file (compass.log)")
                button.clicked.connect(self._open_log_file)
            layout.addWidget(button)

        profile = QPushButton("Yıldırım B.  ▾", self)
        profile.setObjectName("profileButton")
        profile.setFixedHeight(38)
        layout.addWidget(profile)


    def set_active_mode(self, mode: str) -> None:
        self.search.set_plan3d(mode == "PLAN3D")
        for name, button in self.mode_buttons.items():
            active = name == mode
            button.setChecked(active)
            button.setProperty("active", active)
            button.style().unpolish(button)
            button.style().polish(button)

    def _open_log_file(self) -> None:
        from artmach_compass.core.app_logging import log_file_path

        path = log_file_path()
        if path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))
        elif path.parent.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.parent)))


class BottomStatusBar(QFrame):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("bottomStatusBar")
        self.setFixedHeight(38)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 4, 14, 4)
        layout.setSpacing(18)
        layout.addWidget(_label("●  Library: T2_Asset_Library", "statusOk"))
        layout.addSpacing(22)
        layout.addWidget(_label("●  NAS Status: Connected", "statusOk"))
        layout.addSpacing(22)
        layout.addWidget(_label("User: Yıldırım Birinci", "statusText"))
        layout.addStretch(1)
        layout.addWidget(_label("Version: 0.6.1", "statusText"))
        layout.addSpacing(18)
        layout.addWidget(_label("Last Sync: Ready", "statusText"))
        for label in self.findChildren(QLabel):
            label.setStyleSheet("font-size: 10pt;")



class Plan3DInterfaceHistory:
    """Time-stamped snapshots of Compass Plan3D UI state, up to 50 edits."""

    def __init__(self, workspace) -> None:
        self.workspace = workspace
        self.states = [workspace._plan3d_snapshot()]
        self.labels = []
        self.index = 0
        self.restoring = False
        # Temporary reversible examples based on the machine's current local time.
        for number in range(1, 51):
            prior = self.states[-1]
            layers = list(prior["layers"])
            name, semantic, visible = layers[0]
            layers[0] = (name, semantic, not visible)
            self.states.append({"layers": tuple(layers)})
            self.labels.append((datetime.now().astimezone(),
                                f"Demo {number:02d}: {name} visibility"))
        self.index = 50

    def record(self, description: str) -> None:
        if self.restoring:
            return
        state = self.workspace._plan3d_snapshot()
        if state == self.states[self.index]:
            return
        self.states = self.states[:self.index + 1]
        self.labels = self.labels[:self.index]
        self.states.append(state)
        self.labels.append((datetime.now().astimezone(), description))
        if len(self.labels) > 50:
            self.states.pop(0)
            self.labels.pop(0)
        self.index = len(self.states) - 1
        self.workspace._update_history_buttons()

    def go_to(self, index: int) -> None:
        if not 0 <= index < len(self.states) or index == self.index:
            return
        self.restoring = True
        try:
            self.workspace._restore_plan3d_snapshot(self.states[index])
            self.index = index
        finally:
            self.restoring = False
        self.workspace._update_history_buttons()


class CompassWorkspace(QWidget):
    """Responsive, explicit left / middle / right panel composition."""

    PANEL_ORDER = ("library_projects", "preview", "asset_inspector")

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("workspaceDeck")
        self.setAttribute(Qt.WA_StyledBackground, True)

        shell = QVBoxLayout(self)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        self.top_bar = TopCommandBar(self)
        shell.addWidget(self.top_bar)

        self.body = QFrame(self)
        self.body.setObjectName("workspaceBody")
        self._layout = QBoxLayout(QBoxLayout.LeftToRight, self.body)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(8)

        self.left_panel = LibraryProjectFlipPanel(self.body)
        self.center_panel = CenterWorkspacePanel(self.body)
        self.right_panel = InspectorPanel(self.body)
        self.left_panel.library_requested.connect(
            self.center_panel.activate_library
        )
        self.left_panel.project_requested.connect(
            self.center_panel.activate_project
        )
        self.left_panel.ai_requested.connect(
            self.center_panel.activate_ai
        )
        self.center_panel.asset_selected.connect(
            self.right_panel.set_selection
        )

        # This order is the contract that prevents another left/center mix-up.
        self._layout.addWidget(self.left_panel, 0)
        self._layout.addWidget(self.center_panel, 1)
        self._layout.addWidget(self.right_panel, 0)
        shell.addWidget(self.body, 1)
        self.top_bar.mode_requested.connect(self._switch_mode)
        self.left_panel.face_changed.connect(self._activate_mode)
        self.left_panel.plan3d_requested.connect(self._handle_plan3d_command)
        self._history = Plan3DInterfaceHistory(self)
        self.center_panel._plan3d_tools.layer_edited = self._apply_plan3d_layer_changes
        self.top_bar.undo_button.clicked.connect(lambda: self._history.go_to(self._history.index - 1))
        self.top_bar.redo_button.clicked.connect(lambda: self._history.go_to(self._history.index + 1))
        self.top_bar.search.history_requested.connect(self._show_plan3d_history)
        self._update_history_buttons()

        self.status_bar = BottomStatusBar(self)
        shell.addWidget(self.status_bar)

        self._standby_active = False
        self._standby_initialized = True

        self._apply_responsive_layout(1560, 1150)

    def _handle_plan3d_command(self, command: str) -> None:
        if command == "Undo":
            self._history.go_to(self._history.index - 1)
        elif command == "Redo":
            self._history.go_to(self._history.index + 1)
        elif command == "New Project":
            self.center_panel.new_plan3d_project()
        elif command == "Open Project":
            self.center_panel.open_plan3d_project()
        elif command in ("Layers", "Properties", "Project Details"):
            self.center_panel.set_workspace_mode("plan3d")
            self.center_panel.open_plan3d_tool(command)
        else:
            self.center_panel.activate_plan3d(command)

    def _plan3d_snapshot(self) -> dict:
        strip = self.center_panel._plan3d_tools
        layer_rows = strip._panels.get("Layers")
        layers = (tuple((row.name_label.text(), row.semantic.currentText(), row.eye.isChecked())
                        for row in layer_rows.layer_rows)
                  if layer_rows is not None else tuple(strip.layer_state))
        return {"layers": layers}

    def _apply_plan3d_layer_changes(self, description: str) -> None:
        viewport = self.center_panel._active_plan3d_viewport
        if viewport is not None:
            for name, semantic, visible in self.center_panel._plan3d_tools.layer_state:
                viewport.set_layer_type(name, semantic)
                viewport.set_layer_selected(name, visible)
        self._history.record(description)

    def _restore_plan3d_snapshot(self, snapshot: dict) -> None:
        strip = self.center_panel._plan3d_tools
        strip.layer_state = list(snapshot["layers"])
        if "Layers" in strip._panels:
            strip._panels["Layers"].set_layers(list(strip.layer_state))

    def _update_history_buttons(self) -> None:
        self.top_bar.undo_button.setEnabled(self._history.index > 0)
        self.top_bar.redo_button.setEnabled(self._history.index < len(self._history.states) - 1)
        if self._history.index:
            stamp, description = self._history.labels[self._history.index - 1]
            selected = stamp.strftime("%Y-%m-%d %H:%M:%S") + "  " + description
        else:
            selected = "Initial state"
        if self.top_bar.search._plan3d:
            self.top_bar.search.setText(selected)

    def _show_plan3d_history(self) -> None:
        menu = QMenu(self.top_bar.search)
        menu.setStyleSheet("QMenu { background: #1b1b1b; color: #eeeeee; "
                           "border: 1px solid #383838; } "
                           "QMenu::item:selected { background: #383838; }")
        listing = QListWidget(menu)
        listing.setFixedSize(max(390, self.top_bar.search.width()), 340)
        listing.setStyleSheet(
            "QListWidget { background: #1b1b1b; color: #e5e9eb; border: 0; "
            "font-family: Consolas; font-size: 12px; } "
            "QListWidget::item { height: 27px; padding-left: 7px; } "
            "QListWidget::item:hover { background: #383838; } "
            "QListWidget::item:selected { background: #454545; color: #ffffff; }"
        )
        listing.setVerticalScrollBar(ReactiveScrollBar(
            Qt.Vertical, listing, hide_handle_when_idle=True, gradient_track=True
        ))
        for index in range(len(self._history.labels) - 1, -1, -1):
            timestamp, description = self._history.labels[index]
            item = QListWidgetItem(
                f"#{index + 1:02d}  "
                + timestamp.strftime("%Y-%m-%d %H:%M:%S") + "  " + description
            )
            if self._history.index == index + 1:
                item.setBackground(QColor("#454545"))
            item.setData(Qt.UserRole, index + 1)
            listing.addItem(item)
        initial = QListWidgetItem("Initial state")
        initial.setData(Qt.UserRole, 0)
        listing.addItem(initial)
        listing.itemClicked.connect(lambda item: (
            self._history.go_to(item.data(Qt.UserRole)), menu.close()
        ))
        widget_action = QWidgetAction(menu)
        widget_action.setDefaultWidget(listing)
        menu.addAction(widget_action)
        menu.setMinimumWidth(listing.width())
        menu.exec(self.top_bar.search.mapToGlobal(
            self.top_bar.search.rect().bottomLeft()
        ))

    def _switch_mode(self, mode: str) -> None:
        target = {
            "LIBRARY": "library",
            "PROJECTS": "project",
            "AI": "ai",
            "PLAN3D": "plan3d",
        }.get(mode)
        if target is not None:
            if target == self.left_panel._current_mode and self.left_panel._pending_mode is None:
                self.top_bar.set_active_mode(mode)
            else:
                self.left_panel.select_mode(target)

    def _activate_mode(self, mode: str) -> None:
        self.center_panel.set_workspace_mode(mode)
        self.top_bar.set_active_mode({
            "library": "LIBRARY",
            "project": "PROJECTS",
            "ai": "AI",
            "plan3d": "PLAN3D",
        }[mode])
        if mode == "plan3d":
            self._update_history_buttons()

    def set_standby_mode(self, active: bool, *, animated: bool = True) -> None:
        self._standby_active = False
        self.left_panel.setEnabled(True)
        self.right_panel.setEnabled(True)

    def begin_active_reveal(self) -> None:
        self._standby_active = False

    def resizeEvent(self, event) -> None:
        self._apply_responsive_layout(event.size().width(), event.size().height())
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

    def _apply_responsive_layout(self, width: int, height: int) -> None:
        if width >= 1180:
            self._layout.setDirection(QBoxLayout.LeftToRight)
            # Move only the Library rail 5 px closer to the left window edge.
            self._layout.setContentsMargins(17, 14, 22, 14)
            # The side panels already have equal fixed widths and the outer
            # workspace margins are symmetric. A layout gap here was counted
            # only on the Inspector side of the visible separator geometry,
            # making the Library side appear narrower by exactly 8 px.
            self._layout.setSpacing(0)
            self.left_panel.set_edge_alignment(0)
            self._set_horizontal_panel_widths(286)
            return

        if width >= 820:
            self._layout.setDirection(QBoxLayout.LeftToRight)
            # Preserve the same 5 px left-side offset at the medium breakpoint.
            self._layout.setContentsMargins(7, 10, 12, 10)
            # Keep the same mirror geometry at the medium breakpoint.
            self._layout.setSpacing(0)
            self.left_panel.set_edge_alignment(0)
            self._set_horizontal_panel_widths(228)
            return

        self._layout.setDirection(QBoxLayout.TopToBottom)
        self._layout.setContentsMargins(8, 6, 8, 8)
        self._layout.setSpacing(5)
        self.left_panel.set_edge_alignment(5)
        for panel in (self.left_panel, self.center_panel, self.right_panel):
            panel.setMinimumWidth(0)
            panel.setMaximumWidth(16_777_215)
            panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # At the declared 320 × 480 minimum viewport all three semantic regions
        # must stay inside the window. Rich desktop content may clip at this
        # diagnostic size, but the layout itself must never overflow.
        self.left_panel.setMinimumHeight(72)
        self.center_panel.setMinimumHeight(118)
        self.right_panel.setMinimumHeight(72)

    def _set_horizontal_panel_widths(self, side_width: int) -> None:
        self.left_panel.setMinimumHeight(250)
        self.right_panel.setMinimumHeight(250)
        # One shared value prevents the two side panels from drifting apart.
        self.left_panel.setFixedWidth(side_width)
        self.right_panel.setFixedWidth(side_width)
        self.left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.right_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        self.center_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)



# /* PLAN3D_NEUTRAL_GRAY */

# PLAN3D_BLUE_TABS_COMBO_FIX

# PLAN3D_TOOLS_REVEAL_STATUS
