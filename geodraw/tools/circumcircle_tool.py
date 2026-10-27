import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QBrush, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.circumcircle import CircumcircleItem, CircumcenterItem, _circumcenter

_HINTS = [
    "Ngoại tiếp: click điểm A",
    "Ngoại tiếp: click điểm B",
    "Ngoại tiếp: click điểm C",
]


class CircumcircleTool(BaseTool):
    """Click 3 điểm → vẽ đường tròn ngoại tiếp kèm tâm."""
    name = "circumcircle"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._pts: list = []
        self._pts_new: list = []
        self._ghost: QGraphicsEllipseItem = None

    def activate(self):
        self._pts = []
        self._pts_new = []
        self._remove_ghost()
        self.tm.status_hint.emit(_HINTS[0])

    def deactivate(self):
        for pt, is_new in zip(self._pts, self._pts_new):
            if is_new and pt.scene():
                self.scene.removeItem(pt)
        self._pts = []
        self._pts_new = []
        self._remove_ghost()

    def _remove_ghost(self):
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._ghost = None

    def _update_ghost(self, pos: QPointF):
        """Show ghost circle when 2 points fixed + cursor is 3rd."""
        if len(self._pts) != 2:
            self._remove_ghost()
            return
        center, r = _circumcenter(
            self._pts[0].scenePos(), self._pts[1].scenePos(), pos)
        if center is None or r < 1:
            return
        if self._ghost is None:
            self._ghost = QGraphicsEllipseItem()
            self._ghost.setPen(
                QPen(QColor(0, 120, 215, 140), 1.5, Qt.PenStyle.DashLine))
            self._ghost.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)
        self._ghost.setRect(center.x() - r, center.y() - r, r * 2, r * 2)

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return

        snapped_item, snapped_pos = self.scene.snap(pos)
        if snapped_item:
            pt, is_new = snapped_item, False
        else:
            pt = self.scene.new_point(snapped_pos)
            self.scene.addItem(pt)
            is_new = True

        if self._pts and pt is self._pts[-1]:
            return

        self._pts.append(pt)
        self._pts_new.append(is_new)

        n = len(self._pts)
        if n < 3:
            self.tm.status_hint.emit(_HINTS[n])
        else:
            p1, p2, p3 = self._pts
            circle = CircumcircleItem(p1, p2, p3)
            center = CircumcenterItem(p1, p2, p3)
            self.scene.addItem(circle)
            self.scene.addItem(center)

            to_record = [p for p, new in zip(self._pts, self._pts_new) if new]
            to_record.extend([circle, center])
            self.history.push_add_batch(self.scene, to_record)

            self._pts = []
            self._pts_new = []
            self._remove_ghost()
            self.tm.status_hint.emit("✓ Đã vẽ đường tròn ngoại tiếp (tâm O tự động)")

    def move(self, pos: QPointF, modifiers):
        self._update_ghost(pos)

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)
