from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsLineItem
from PyQt6.QtGui import QPen, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.line import LineItem, RayItem
from items.segment import SegmentItem
from utils.collinear import segment_exists


class _TwoPointTool(BaseTool):
    """Shared base for Line and Ray tools."""
    _item_class = None

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._p1: PointItem = None
        self._p1_new = False
        self._ghost = None

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
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._ghost = None

    def _ensure_ghost(self):
        if self._ghost is None:
            self._ghost = QGraphicsLineItem()
            self._ghost.setPen(QPen(QColor(100, 100, 100, 120), 1.2,
                                    Qt.PenStyle.DashLine))
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        snapped_item, snapped_pos = self.scene.snap(pos)
        if self._p1 is None:
            if snapped_item:
                self._p1, self._p1_new = snapped_item, False
            else:
                pt = PointItem(snapped_pos)
                self.scene.addItem(pt)
                self._p1, self._p1_new = pt, True
            self._ensure_ghost()
        else:
            if snapped_item and snapped_item is self._p1:
                return
            if snapped_item:
                pt2, pt2_new = snapped_item, False
            else:
                pt2 = PointItem(snapped_pos)
                self.scene.addItem(pt2)
                pt2_new = True

            item = self._item_class(self._p1, pt2)
            self.scene.addItem(item)
            to_record = (
                ([self._p1] if self._p1_new else []) +
                ([pt2] if pt2_new else []) +
                [item]
            )

            # ── Tự động tạo đoạn thẳng nối 2 điểm (chỉ với LineItem) ──
            if isinstance(item, LineItem) and \
                    not segment_exists(self.scene, self._p1, pt2):
                seg = SegmentItem(self._p1, pt2)
                self.scene.addItem(seg)
                to_record = list(to_record) + [seg]

            if len(to_record) == 1:
                self.history.push_add(self.scene, to_record[0])
            else:
                self.history.push_add_batch(self.scene, to_record)
            self._p1 = None
            self._p1_new = False
            self._remove_ghost()

    def move(self, pos: QPointF, modifiers):
        if self._p1 and self._ghost:
            p1s = self._p1.scenePos()
            _, snapped = self.scene.snap(pos, exclude=self._p1)
            self._ghost.setLine(p1s.x(), p1s.y(), snapped.x(), snapped.y())

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)


class LineTool(_TwoPointTool):
    name = "line"
    _item_class = LineItem


class RayTool(_TwoPointTool):
    name = "ray"
    _item_class = RayItem
