"""Fix missing Plan3D tool-panel controls without replacing Compass UI code."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parent
target = root / "artmach_compass" / "ui" / "workspace.py"
source = target.read_text(encoding="utf-8")
anchor = "class Plan3DLayerRow(QFrame):"
if source.count(anchor) != 1:
    raise SystemExit("Plan3D panel anchor was not found exactly once. No changes made.")
classes = {node.name for node in ast.parse(source).body if isinstance(node, ast.ClassDef)}
missing = []
for name, definition in (("Plan3DEyeButton", 'class Plan3DEyeButton(QToolButton):\n    """Layer visibility control drawn at the display\'s native resolution."""\n\n    def __init__(self, visible: bool, parent: QWidget | None = None) -> None:\n        super().__init__(parent)\n        self.setObjectName("plan3dEyeButton")\n        self.setCheckable(True)\n        self.setChecked(visible)\n        self.setFixedSize(25, 22)\n        self.setCursor(Qt.PointingHandCursor)\n\n    def paintEvent(self, event) -> None:\n        super().paintEvent(event)\n        painter = QPainter(self)\n        painter.setRenderHint(QPainter.Antialiasing, True)\n        color = QColor("#e0e0e0" if self.isChecked() else "#858585")\n        painter.setPen(QPen(color, 1.35))\n        painter.setBrush(Qt.NoBrush)\n        width, height = self.width(), self.height()\n        outline = QPainterPath()\n        outline.moveTo(4.5, height / 2)\n        outline.cubicTo(8, 5.5, width - 8, 5.5, width - 4.5, height / 2)\n        outline.cubicTo(width - 8, height - 5.5, 8, height - 5.5, 4.5, height / 2)\n        painter.drawPath(outline)\n        painter.setBrush(color if self.isChecked() else Qt.NoBrush)\n        painter.drawEllipse(QRectF(width / 2 - 2.7, height / 2 - 2.7, 5.4, 5.4))\n'), ("Plan3DPanelButton", 'class Plan3DPanelButton(QToolButton):\n    """Compact close and refresh icons for the tool-panel headers."""\n\n    def __init__(self, symbol: str, parent: QWidget | None = None) -> None:\n        super().__init__(parent)\n        self.symbol = symbol\n        self.setObjectName("plan3dHeaderButton")\n        self.setFixedSize(27, 26)\n        self.setCursor(Qt.PointingHandCursor)\n\n    def paintEvent(self, event) -> None:\n        super().paintEvent(event)\n        painter = QPainter(self)\n        painter.setRenderHint(QPainter.Antialiasing, True)\n        color = QColor("#f39743" if self.underMouse() else "#d2d2d2")\n        painter.setPen(QPen(color, 1.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))\n        if self.symbol == "close":\n            painter.drawLine(QPointF(9, 9), QPointF(18, 17))\n            painter.drawLine(QPointF(18, 9), QPointF(9, 17))\n        elif self.symbol == "refresh":\n            arc = QPainterPath()\n            arc.moveTo(18.5, 10)\n            arc.cubicTo(16.8, 6.5, 11.8, 6.2, 9, 9)\n            arc.cubicTo(5.5, 12.5, 8.4, 18.7, 13.5, 19)\n            arc.cubicTo(16.1, 19.1, 18.2, 17.3, 19.2, 15.3)\n            painter.drawPath(arc)\n            painter.drawLine(QPointF(18.5, 10), QPointF(18.4, 5.9))\n            painter.drawLine(QPointF(18.5, 10), QPointF(14.6, 9.4))\n')):
    if name not in classes:
        missing.append(definition)
if not missing:
    print("Plan3D panel controls are already installed.")
else:
    updated = source.replace(anchor, "\n\n".join(missing) + "\n\n" + anchor, 1)
    compile(updated, str(target), "exec")
    target.with_suffix(".py.before_panel_fix").write_text(source, encoding="utf-8")
    target.write_text(updated, encoding="utf-8")
    print("Restored Plan3D panel controls:", ", ".join(name for name in ("Plan3DEyeButton", "Plan3DPanelButton") if name not in classes))
