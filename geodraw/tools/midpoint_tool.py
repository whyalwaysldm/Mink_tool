from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtWidgets import QGraphicsLineItem
from PyQt6.QtGui import QPen, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.midpoint import MidpointItem
from items.segment import SegmentItem


class MidpointTool(BaseTool):
    """Click 2 điểm (hoặc click lên đoạn thẳng) để tạo trung điểm."""
    name = "midpoint"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._p1: PointItem = None
        self._p1_new = False
        self._ghost = None

    def activate(self):
        self._p1 = None
        self._p1_new = False
        self._remove_ghost()
        self.tm.status_hint.emit(
            "Trung điểm: click điểm thứ nhất  —  hoặc click thẳng lên đoạn thẳng")

    def deactivate(self):
        if self._p1 and self._p1_new and self._p1.scene():
            self.scene.removeItem(self._p1)
        self._p1 = None
        self._p1_new = False
        self._remove_ghost()

    # ── ghost helpers ────────────────────────────────────────────────────
    def _remove_ghost(self):
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._ghost = None

    def _ensure_ghost(self):
        if self._ghost is None:
            self._ghost = QGraphicsLineItem()
            pen = QPen(QColor(0, 120, 215, 140), 1.5, Qt.PenStyle.DashLine)
            self._ghost.setPen(pen)
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)

    # ── hit-test helpers ─────────────────────────────────────────────────
    def _segment_at(self, pos) -> SegmentItem:
        for item in self.scene.items(QRectF(pos.x() - 6, pos.y() - 6, 12, 12)):
            if isinstance(item, SegmentItem):
                return item
        return None

    # ── events ──────────────────────────────────────────────────────────
    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return

        snapped_item, snapped_pos = self.scene.snap(pos)

        # ── no first point yet ──
        if self._p1 is None:
            # Shortcut: click directly on a segment
            seg = self._segment_at(pos)
            if seg and not snapped_item:
                mid = MidpointItem(seg.p1, seg.p2)
                self.scene.addItem(mid)
                from utils.collinear import auto_segments_for_new_point
                auto_segs = auto_segments_for_new_point(self.scene, mid)
                all_items = [mid] + auto_segs
                if len(all_items) == 1:
                    self.history.push_add(self.scene, mid)
                else:
                    self.history.push_add_batch(self.scene, all_items)
                self.tm.status_hint.emit("✓ Đã tạo trung điểm")
                return

            if snapped_item:
                self._p1 = snapped_item
                self._p1_new = False
            else:
                self._p1 = self.scene.new_point(snapped_pos)
                self.scene.addItem(self._p1)
                self._p1_new = True

            self._ensure_ghost()
            self.tm.status_hint.emit("Trung điểm: click điểm thứ hai")

        # ── first point already chosen ──
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

            mid = MidpointItem(self._p1, pt2)
            self.scene.addItem(mid)
            from utils.collinear import auto_segments_for_new_point
            auto_segs = auto_segments_for_new_point(self.scene, mid)

            to_record = []
            if self._p1_new:
                to_record.append(self._p1)
            if pt2_new:
                to_record.append(pt2)
            to_record.append(mid)
            to_record.extend(auto_segs)
            self.history.push_add_batch(self.scene, to_record)

            self._p1 = None
            self._p1_new = False
            self._remove_ghost()
            self.tm.status_hint.emit("✓ Đã tạo trung điểm")

    def move(self, pos: QPointF, modifiers):
        if self._p1 and self._ghost:
            p1s = self._p1.scenePos()
            _, snapped = self.scene.snap(pos, exclude=self._p1)
            self._ghost.setLine(p1s.x(), p1s.y(), snapped.x(), snapped.y())

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)
