import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QTransform
from .base_tool import BaseTool
from items.segment import SegmentItem
from items.line import RayItem
from items.bisector_ray import BisectorRayItem
from tools.measure_tool import _shared_vertex, _are_collinear, _angle_at

# Ngưỡng "cùng vị trí" để cycle (px manhattan)
_SAME_POS_DIST = 20.0


class AngleBisectorTool(BaseTool):
    """
    Vẽ tia phân giác góc — chỉ cần chọn 2 đoạn/tia chung đỉnh.

    Cách dùng
    ─────────
    A. Chọn trước bằng SelectTool rồi nhấn J:
       1. Esc  → SelectTool.
       2. Click đoạn 1, Shift+click đoạn 2 chung đỉnh.
       3. J → tia phân giác được vẽ ngay lập tức.

    B. Dùng thẳng trong AngleBisectorTool:
       1. J  → vào tool.
       2. Click đoạn/tia 1 → highlight.
       3. Click đoạn/tia 2 chung đỉnh → phân giác vẽ ngay.
          (Click cùng vị trí → cycle qua các đoạn chồng nhau)

    Esc → huỷ chọn hiện tại.
    """

    name = "angle_bisector"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._sel: list = []       # list[SegmentItem | RayItem], tối đa 2
        self._cyc_pos  = None      # QPointF
        self._cyc_segs: list = []  # items tại vị trí cycle
        self._cyc_last = None      # item đã pick lần trước

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def activate(self):
        # Nhập selection từ SelectTool (nếu có)
        existing = [it for it in self.scene.selectedItems()
                    if isinstance(it, (SegmentItem, RayItem))]
        self._sel      = existing[:2]
        self._cyc_pos  = None
        self._cyc_segs = []
        self._cyc_last = None

        # Đồng bộ Qt visual
        self.scene.clearSelection()
        for s in self._sel:
            s.setSelected(True)

        # Nếu selection sẵn đã đủ 2 đoạn hợp lệ → vẽ ngay
        if not self._try_draw():
            self._emit_state_hint()

    def deactivate(self):
        self._sel      = []
        self._cyc_pos  = None
        self._cyc_segs = []
        self._cyc_last = None
        self.scene.clearSelection()

    # ── Event: click ──────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return

        items = self._items_at(pos)

        # Click vùng trống → reset
        if not items:
            self._sel      = []
            self._cyc_pos  = None
            self._cyc_segs = []
            self._cyc_last = None
            self.scene.clearSelection()
            self._emit_hint()
            return

        # ── Cycle hoặc pick mới ───────────────────────────────────────
        same_pos = (
            self._cyc_pos is not None
            and (pos - self._cyc_pos).manhattanLength() <= _SAME_POS_DIST
        )

        if same_pos and self._cyc_last is not None and len(items) > 1:
            try:
                prev_idx = next(i for i, it in enumerate(items)
                                if it is self._cyc_last)
                idx = (prev_idx + 1) % len(items)
            except StopIteration:
                idx = 0
            picked = items[idx]
            if self._cyc_last in self._sel:
                self._sel.remove(self._cyc_last)
        else:
            picked = items[0]

        self._cyc_pos  = QPointF(pos)
        self._cyc_segs = items
        self._cyc_last = picked

        if picked not in self._sel:
            self._sel.append(picked)
            # Giữ tối đa 2: nếu thêm đoạn thứ 3 → bỏ đoạn cũ nhất
            if len(self._sel) > 2:
                self._sel.pop(0)

        # Visual
        self.scene.clearSelection()
        for s in self._sel:
            s.setSelected(True)

        # Thử vẽ ngay nếu đủ 2 đoạn hợp lệ
        if not self._try_draw():
            self._emit_state_hint()

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Escape:
            self._sel      = []
            self._cyc_pos  = None
            self._cyc_segs = []
            self._cyc_last = None
            self.scene.clearSelection()
            self._emit_hint()

    # ── Vẽ phân giác ──────────────────────────────────────────────────────

    def _try_draw(self) -> bool:
        """
        Nếu có đúng 2 item chung đỉnh, không thẳng hàng → vẽ tia phân giác.
        Trả True nếu đã vẽ.
        """
        if len(self._sel) != 2:
            return False

        rv = _shared_vertex(self._sel[0], self._sel[1])
        if rv is None:
            return False
        vertex, arm1, arm2 = rv
        if _are_collinear(vertex, arm1, arm2):
            self.tm.status_hint.emit(
                "2 đoạn thẳng hàng — không tạo được phân giác; chọn đoạn khác")
            return False

        # Vẽ tia phân giác
        ray = BisectorRayItem(arm1, vertex, arm2)
        self.scene.addItem(ray)
        self.history.push_add(self.scene, ray)

        ang = _angle_at(vertex, arm1, arm2)
        self.tm.status_hint.emit(
            f"✓ Tia phân giác góc {ang:.1f}°   —   click 2 đoạn tiếp theo | Esc: thoát")

        # Reset sẵn sàng cho lần vẽ tiếp
        self._sel      = []
        self._cyc_pos  = None
        self._cyc_segs = []
        self._cyc_last = None
        self.scene.clearSelection()
        return True

    # ── Helpers ───────────────────────────────────────────────────────────

    def _items_at(self, pos: QPointF) -> list:
        """Tất cả SegmentItem / RayItem tại pos (ngắn trước, tia sau)."""
        view = self.scene.views()[0] if self.scene.views() else None
        t    = view.transform() if view else QTransform()
        result = []
        for item in self.scene.items(
                pos,
                Qt.ItemSelectionMode.IntersectsItemShape,
                Qt.SortOrder.DescendingOrder,
                t):
            if isinstance(item, (SegmentItem, RayItem)):
                result.append(item)
        # Sắp xếp: đoạn ngắn trước, tia sau (RayItem = độ dài vô hạn)
        result.sort(key=lambda it: (
            it.length() if isinstance(it, SegmentItem) else float('inf')
        ))
        return result

    def _emit_hint(self):
        self.tm.status_hint.emit(
            "Phân giác: click đoạn/tia 1 → click đoạn/tia 2 chung đỉnh → vẽ ngay")

    def _emit_state_hint(self):
        n = len(self._sel)
        if n == 0:
            self._emit_hint()
        elif n == 1:
            self.tm.status_hint.emit(
                "Phân giác: đã chọn 1 đoạn/tia — click đoạn/tia 2 chung đỉnh")
        else:
            self.tm.status_hint.emit(
                "2 đoạn/tia không chung đỉnh — click đoạn khác hoặc Esc")
