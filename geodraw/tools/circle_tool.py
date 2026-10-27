from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsEllipseItem
from PyQt6.QtGui import QPen, QBrush, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.circle import CircleItem
import math


class CircleTool(BaseTool):
    name = "circle"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._center: PointItem = None
        self._center_new = False
        self._ghost = None

    def activate(self):
        self._center = None
        self._center_new = False
        self._remove_ghost()

    def deactivate(self):
        if self._center and self._center_new and self._center.scene():
            self.scene.removeItem(self._center)
        self._center = None
        self._center_new = False
        self._remove_ghost()

    def _remove_ghost(self):
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._ghost = None

    def _ensure_ghost(self):
        if self._ghost is None:
            self._ghost = QGraphicsEllipseItem(0, 0, 1, 1)
            self._ghost.setPen(QPen(QColor(0, 120, 215, 140), 1.5,
                                    Qt.PenStyle.DashLine))
            self._ghost.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        snapped_item, snapped_pos = self.scene.snap(pos)

        if self._center is None:
            if snapped_item:
                self._center = snapped_item
                self._center_new = False
            else:
                pt = self.scene.new_point(snapped_pos)
                self.scene.addItem(pt)
                self._center = pt
                self._center_new = True
            self._ensure_ghost()
        else:
            if snapped_item:
                rpt = snapped_item
                rpt_new = False
            else:
                rpt = self.scene.new_point(snapped_pos)
                self.scene.addItem(rpt)
                rpt_new = True

            circle = CircleItem(self._center, rpt)
            self.scene.addItem(circle)

            to_record = []
            if self._center_new:
                to_record.append(self._center)
            if rpt_new:
                to_record.append(rpt)
            to_record.append(circle)

            if len(to_record) == 1:
                self.history.push_add(self.scene, to_record[0])
            else:
                self.history.push_add_batch(self.scene, to_record)

            self._center = None
            self._center_new = False
            self._remove_ghost()

    def move(self, pos: QPointF, modifiers):
        if self._center and self._ghost:
            sc = self._center.scenePos()
            _, snapped = self.scene.snap(pos, exclude=self._center)
            dx = snapped.x() - sc.x()
            dy = snapped.y() - sc.y()
            r = math.sqrt(dx*dx + dy*dy)
            self._ghost.setRect(sc.x() - r, sc.y() - r, r * 2, r * 2)

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)
