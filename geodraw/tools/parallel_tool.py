from PyQt6.QtCore import Qt, QPointF, QRectF
from .base_tool import BaseTool
from items.point import PointItem
from items.segment import SegmentItem
from items.line import LineItem, RayItem
from items.constructed import FootPointItem, DirectionPointItem


class _ThroughPointTool(BaseTool):
    """
    Click 1 điểm (có sẵn hoặc chỗ trống → tạo điểm mới),
    rồi click 1 đường (đoạn / đường thẳng / tia) → vẽ đường thẳng qua điểm đó.
    Đường mới tự cập nhật khi kéo điểm hoặc đường gốc.
    """
    perpendicular = False
    title = ""

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._pt: PointItem = None
        self._pt_new = False

    def activate(self):
        self._reset(remove_new=True)
        self.tm.status_hint.emit(f"{self.title}: click vào điểm")

    def deactivate(self):
        self._reset(remove_new=True)

    def _reset(self, remove_new: bool):
        if remove_new and self._pt is not None and self._pt_new \
                and self._pt.scene():
            self.scene.removeItem(self._pt)
        if self._pt is not None and self._pt.scene():
            self._pt.setSelected(False)
        self._pt = None
        self._pt_new = False

    def _line_at(self, pos: QPointF):
        """Đoạn / đường thẳng / tia gần pos nhất (theo vùng click của nó)."""
        r = 6.0
        for item in self.scene.items(QRectF(pos.x() - r, pos.y() - r, 2 * r, 2 * r)):
            if isinstance(item, (SegmentItem, LineItem, RayItem)) \
                    and item.isVisible():
                return item
        return None

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return

        # ── Bước 1: chọn điểm ─────────────────────────────────────────
        if self._pt is None:
            snapped_item, snapped_pos = self.scene.snap(pos)
            if isinstance(snapped_item, PointItem):
                self._pt, self._pt_new = snapped_item, False
            else:
                self._pt = PointItem(snapped_pos)
                self.scene.addItem(self._pt)
                self._pt_new = True
            self.scene.clearSelection()
            self._pt.setSelected(True)
            self.tm.status_hint.emit(
                f"{self.title}: click vào đường thẳng / đoạn thẳng / tia")
            return

        # ── Bước 2: chọn đường ────────────────────────────────────────
        line = self._line_at(pos)
        if line is None:
            self.tm.status_hint.emit(
                f"{self.title}: hãy click đúng vào một đường thẳng / đoạn thẳng / tia"
                "  (Esc để chọn lại điểm)")
            return
        a = self._pt
        new_items = [a] if self._pt_new else []
        helper = DirectionPointItem(a, line.p1, line.p2, self.perpendicular)
        new_line = LineItem(a, helper)
        new_items += [helper, new_line]
        if self.perpendicular:
            foot = FootPointItem(a, line.p1, line.p2)
            new_items.append(foot)
        for it in new_items:
            if it.scene() is None:
                self.scene.addItem(it)
        self.history.push_add_batch(self.scene, new_items)
        self._pt_new = False          # đã đưa vào lịch sử, không xóa nữa
        self._reset(remove_new=False)
        self.tm.status_hint.emit(f"✓ Đã vẽ {self.title.lower()} — click điểm tiếp theo")

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Escape:
            self.deactivate()
            self.activate()


class ParallelTool(_ThroughPointTool):
    name = "parallel"
    perpendicular = False
    title = "Đường song song"


class PerpendicularTool(_ThroughPointTool):
    name = "perpendicular"
    perpendicular = True
    title = "Đường vuông góc"
