from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtWidgets import QApplication
from .base_tool import BaseTool
from items.point import PointItem
from items.segment import SegmentItem
from items.line import LineItem, RayItem
from items.circle import CircleItem
from items.constructed import (FootPointItem, DirectionPointItem,
                                RadiusPointItem)

_LINE_TYPES = (SegmentItem, LineItem, RayItem)


class _ThroughPointTool(BaseTool):
    """
    Vẽ đường thẳng qua điểm, song song / vuông góc với một đường.

    • Click điểm, rồi click đường → 1 đường mới.
    • Ctrl + click nhiều điểm, rồi click 1 đường → mỗi điểm 1 đường mới.
    • Click 1 điểm, rồi Ctrl + click nhiều đường → mỗi đường 1 đường mới
      (giữ Ctrl thì điểm vẫn được giữ để click tiếp đường khác).
    • Chọn sẵn điểm + đường bằng công cụ Chọn (Ctrl + click), rồi bật công cụ
      này → vẽ ngay cho mọi cặp điểm – đường đã chọn.
    Đường mới tự cập nhật khi kéo điểm hoặc đường gốc.
    """
    perpendicular = False
    title = ""
    line_types = _LINE_TYPES
    line_word = "đường"            # tên đối tượng thứ hai trong thông báo

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._pts: list = []          # điểm đã chọn
        self._new_pts: list = []      # điểm mới tạo (chưa vào lịch sử)

    # ── Lifecycle ─────────────────────────────────────────────────────

    def activate(self):
        self._pts, self._new_pts = [], []
        if self._build_from_selection():
            return
        self.tm.status_hint.emit(
            f"{self.title}: click điểm (Ctrl + click để chọn nhiều điểm)")

    def deactivate(self):
        for p in self._new_pts:
            if p.scene():
                self.scene.removeItem(p)
        for p in self._pts:
            if p.scene():
                p.setSelected(False)
        self._pts, self._new_pts = [], []

    def _build_from_selection(self) -> bool:
        """Điểm + đường đã chọn sẵn (công cụ Chọn) → vẽ cho mọi cặp."""
        sel = self.scene.selectedItems()
        pts = [it for it in sel if isinstance(it, PointItem)]
        lines = [it for it in sel if isinstance(it, self.line_types)]
        if not pts or not lines:
            return False
        n = self._create(pts, lines, new_points=[])
        self.scene.clearSelection()
        self.tm.status_hint.emit(
            f"✓ Đã vẽ {n} {self.title.lower()} từ các đối tượng đã chọn")
        return True

    # ── Helpers ───────────────────────────────────────────────────────

    def _line_at(self, pos: QPointF):
        """Đoạn / đường thẳng / tia gần pos."""
        r = 6.0
        for item in self.scene.items(QRectF(pos.x() - r, pos.y() - r, 2 * r, 2 * r)):
            if isinstance(item, self.line_types) and item.isVisible():
                return item
        return None

    def _create(self, pts: list, lines: list, new_points: list) -> int:
        """Tạo đường cho mọi cặp (điểm, đường); 1 bước undo. Trả về số đường."""
        items = list(new_points)
        count = 0
        for a in pts:
            for line in lines:
                made = self._make(a, line)
                if made:
                    items += made
                    count += 1
        if not count:
            return 0
        for it in items:
            if it.scene() is None:
                self.scene.addItem(it)
        self.history.push_add_batch(self.scene, items)
        return count

    def _make(self, a: PointItem, line) -> list:
        """Đối tượng mới cho cặp (điểm a, đường line); [] nếu bỏ qua."""
        if not self.perpendicular and (a is line.p1 or a is line.p2):
            return []                 # song song qua điểm nằm trên đường = chính nó
        helper = DirectionPointItem(a, line.p1, line.p2, self.perpendicular)
        items = [helper, LineItem(a, helper)]
        on_line = (a is line.p1 or a is line.p2 or
                   getattr(a, 'host', None) is line)
        if self.perpendicular and not on_line:
            # Điểm nằm trên đường → chân đường vuông góc trùng chính nó
            items.append(FootPointItem(a, line.p1, line.p2))
        return items

    # ── Events ────────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        mods = modifiers | QApplication.keyboardModifiers()   # bút không gửi kèm phím
        ctrl = bool(mods & Qt.KeyboardModifier.ControlModifier)

        snapped_item, snapped_pos = self.scene.snap(pos)
        line = None if isinstance(snapped_item, PointItem) else self._line_at(pos)

        # ── Click vào đường (đã có điểm) → vẽ ─────────────────────────
        if line is not None and self._pts:
            keep = [p for p in self._new_pts if p in self._pts]
            for p in self._new_pts:
                if p not in keep and p.scene():
                    self.scene.removeItem(p)   # điểm mới đã bị bỏ chọn
            n = self._create(self._pts, [line], keep)
            self._new_pts = []        # đã vào lịch sử
            if ctrl and len(self._pts) == 1:
                # Giữ Ctrl: giữ điểm để click tiếp đường khác
                self.tm.status_hint.emit(
                    f"✓ Đã vẽ {self.title.lower()} — Ctrl + click {self.line_word} khác, "
                    "hoặc click điểm mới")
                return
            for p in self._pts:
                p.setSelected(False)
            self._pts = []
            self.tm.status_hint.emit(
                f"✓ Đã vẽ {n} {self.title.lower()} — click điểm tiếp theo")
            return

        if line is not None and snapped_item is None:
            self.tm.status_hint.emit(f"{self.title}: hãy click vào điểm trước")
            return

        # ── Click vào điểm (hoặc chỗ trống → tạo điểm) ────────────────
        if isinstance(snapped_item, PointItem):
            pt = snapped_item
        else:
            pt = self.scene.new_point(snapped_pos)
            self.scene.addItem(pt)
            self._new_pts.append(pt)

        if ctrl:
            if pt in self._pts:       # Ctrl + click lại → bỏ chọn
                self._pts.remove(pt)
                pt.setSelected(False)
            else:
                self._pts.append(pt)
                pt.setSelected(True)
        else:
            for p in self._pts:
                p.setSelected(False)
            self._pts = [pt]
            pt.setSelected(True)
        k = len(self._pts)
        self.tm.status_hint.emit(
            f"{self.title}: đã chọn {k} điểm — click vào {self.line_word} "
            "(Ctrl + click để chọn thêm điểm / vẽ tới nhiều đường)")

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


class CompassTool(_ThroughPointTool):
    """Đường tròn tâm là điểm, bán kính bằng độ dài đoạn thẳng.
       Nhiều tâm + 1 đoạn → các đường tròn cùng bán kính;
       1 tâm + nhiều đoạn → các đường tròn đồng tâm."""
    name = "compass"
    title = "Đường tròn (bán kính = đoạn)"
    line_types = (SegmentItem,)
    line_word = "đoạn thẳng"

    def _make(self, a: PointItem, seg) -> list:
        r = RadiusPointItem(a, seg.p1, seg.p2)
        return [r, CircleItem(a, r)]
