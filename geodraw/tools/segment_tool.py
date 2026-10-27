from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsLineItem
from PyQt6.QtGui import QPen, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.segment import SegmentItem


class SegmentTool(BaseTool):
    name = "segment"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._p1: PointItem = None
        self._p1_new = False
        self._ghost_line = None

    def activate(self):
        self._p1 = None
        self._p1_new = False
        self._remove_ghost()

    def deactivate(self):
        if self._p1 and self._p1_new and self._p1.scene():
            self.scene.removeItem(self._p1)
        self._p1 = None
        self._p1_new = False
        self._remove_ghost()

    def _remove_ghost(self):
        if self._ghost_line and self._ghost_line.scene():
            self.scene.removeItem(self._ghost_line)
        self._ghost_line = None

    def _ensure_ghost(self):
        if self._ghost_line is None:
            self._ghost_line = QGraphicsLineItem()
            pen = QPen(QColor(0, 120, 215, 140), 1.5, Qt.PenStyle.DashLine)
            self._ghost_line.setPen(pen)
            self._ghost_line.setZValue(50)
            self.scene.addItem(self._ghost_line)

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        snapped_item, snapped_pos = self.scene.snap(pos)

        if self._p1 is None:
            if snapped_item:
                self._p1 = snapped_item
                self._p1_new = False
            else:
                pt = self.scene.new_point(snapped_pos)
                self.scene.addItem(pt)
                self._p1 = pt
                self._p1_new = True
            self._ensure_ghost()
        else:
            if snapped_item and snapped_item is self._p1:
                return
            if snapped_item:
                pt2 = snapped_item
                pt2_new = False
            else:
                pt2 = self.scene.new_point(snapped_pos)
                self.scene.addItem(pt2)
                pt2_new = True

            seg = SegmentItem(self._p1, pt2)
            self.scene.addItem(seg)

            to_record = []
            if self._p1_new:
                to_record.append(self._p1)
            if pt2_new:
                to_record.append(pt2)
            to_record.append(seg)

            if len(to_record) == 1:
                self.history.push_add(self.scene, to_record[0])
            else:
                self.history.push_add_batch(self.scene, to_record)

            self._p1 = None
            self._p1_new = False
            self._remove_ghost()

    def move(self, pos: QPointF, modifiers):
        if self._p1 and self._ghost_line:
            p1_scene = self._p1.scenePos()
            _, snapped = self.scene.snap(pos, exclude=self._p1)
            self._ghost_line.setLine(p1_scene.x(), p1_scene.y(),
                                     snapped.x(), snapped.y())

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)
