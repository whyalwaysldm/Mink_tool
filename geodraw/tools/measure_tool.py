import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QTransform
from .base_tool import BaseTool
from items.segment import SegmentItem
from items.measure import SegmentMeasureItem, AngleMeasureItem

# ── Ngưỡng nhận ra "cùng vị trí" để cycle (px manhattan) ────────────────────
_SAME_POS_DIST = 20.0
# Ngưỡng thẳng hàng: |sin(góc)| < sin(5°) ≈ 0.087
_COLLINEAR_SIN = 0.087


class MeasureTool(BaseTool):
    """
    Công cụ đo đạc — tách biệt hoàn toàn việc CHỌN và ĐO.

    Cách dùng
    ─────────
    Bước 1 — Chọn đoạn/tia:
      • Click đoạn thẳng → thêm vào danh sách chọn (highlight xanh).
      • Click cùng vị trí nhiều lần → cycle qua các đoạn chồng nhau
        (đoạn cũ bị thay bằng đoạn tiếp theo tại đó).
      • Click vùng trống → bỏ chọn tất cả.

    Bước 2 — Đo (Enter):
      • 1 đoạn → nhãn độ dài "ℓ = X.X".
      • 2 đoạn chung đỉnh, không thẳng hàng → nhãn góc "∠ = X.X°" (chỉ góc, không đo dài).
      • 2 đoạn không chung đỉnh, hoặc ≥ 3 đoạn → nhãn độ dài cho mỗi đoạn.

    Esc  → huỷ chọn (nhãn đã tạo vẫn giữ).
    ─────────────────────────────────────────────────────────────────────────
    Workflow nhanh (chọn trước bằng SelectTool):
      1. Esc  → SelectTool.
      2. Click đoạn 1, Shift+click đoạn 2 → 2 đoạn được chọn.
      3. D    → vào MeasureTool; selection được nhập tự động.
      4. Enter → tạo nhãn góc/độ dài.
    ─────────────────────────────────────────────────────────────────────────
    Nhãn tự cập nhật khi kéo điểm. Chọn nhãn + Delete để xoá.
    """

    name = "measure"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        # Danh sách đoạn đang được chọn (tích lũy)
        self._sel: list = []           # list[SegmentItem]
        # Trạng thái cycle "cùng vị trí"
        self._cyc_pos  = None          # QPointF
        self._cyc_segs: list = []      # list[SegmentItem] tại vị trí đó
        self._cyc_last = None          # SegmentItem — đã pick lần trước

    # ── Lifecycle ─────────────────────────────────────────────────────────

    def activate(self):
        # Nhập selection hiện có từ SelectTool (Shift+click trước đó)
        existing = [it for it in self.scene.selectedItems()
                    if isinstance(it, SegmentItem)]
        self._sel      = existing
        self._cyc_pos  = None
        self._cyc_segs = []
        self._cyc_last = None
        # Đảm bảo Qt selection đồng bộ
        self.scene.clearSelection()
        for s in self._sel:
            s.setSelected(True)
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

        segs = self._segs_at(pos)

        # Click vùng trống → bỏ chọn tất cả
        if not segs:
            self._sel      = []
            self._cyc_pos  = None
            self._cyc_segs = []
            self._cyc_last = None
            self.scene.clearSelection()
            self._emit_hint()
            return

        # ── Xác định đoạn sẽ pick (cycle nếu cùng vị trí) ───────────
        same_pos = (
            self._cyc_pos is not None
            and (pos - self._cyc_pos).manhattanLength() <= _SAME_POS_DIST
        )

        if same_pos and self._cyc_last is not None and len(segs) > 1:
            # Tiến sang đoạn tiếp theo trong cycle
            try:
                prev_idx = next(i for i, s in enumerate(segs)
                                if s is self._cyc_last)
                idx = (prev_idx + 1) % len(segs)
            except StopIteration:
                idx = 0
            picked = segs[idx]
            # Gỡ đoạn cũ ở vị trí này ra khỏi _sel
            if self._cyc_last in self._sel:
                self._sel.remove(self._cyc_last)
        else:
            # Vị trí mới: chọn đoạn ngắn nhất (hoặc duy nhất)
            picked = segs[0]

        # Cập nhật cycle state
        self._cyc_pos  = QPointF(pos)
        self._cyc_segs = segs
        self._cyc_last = picked

        # Thêm vào _sel (nếu chưa có)
        if picked not in self._sel:
            self._sel.append(picked)

        # Cập nhật Qt visual
        self.scene.clearSelection()
        for s in self._sel:
            s.setSelected(True)

        self._emit_state_hint()

    # ── Event: phím ───────────────────────────────────────────────────────

    def key_press(self, key, modifiers):
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit()
        elif key == Qt.Key.Key_Escape:
            self._sel      = []
            self._cyc_pos  = None
            self._cyc_segs = []
            self._cyc_last = None
            self.scene.clearSelection()
            self._emit_hint()

    # ── Đo lường (Enter) ─────────────────────────────────────────────────

    def _commit(self):
        """Tạo nhãn dựa trên _sel, rồi xoá selection."""
        segs = list(self._sel)
        n    = len(segs)

        if n == 0:
            self.tm.status_hint.emit(
                "Chưa chọn đoạn nào — click đoạn thẳng để chọn")
            return

        results = []

        if n == 1:
            # ── Đo độ dài 1 đoạn ────────────────────────────────────
            if self._add_seg_measure(segs[0]):
                results.append(f"ℓ = {_seg_len(segs[0]):.1f}")

        elif n == 2:
            rv = _shared_vertex(segs[0], segs[1])
            if rv and not _are_collinear(*rv):
                # ── Đo góc giữa 2 đoạn chung đỉnh ──────────────────
                vertex, arm1, arm2 = rv
                if self._add_angle_measure(vertex, arm1, arm2):
                    results.append(f"∠ = {_angle_at(vertex, arm1, arm2):.1f}°")
            else:
                # 2 đoạn không chung đỉnh (hoặc thẳng hàng) → độ dài cả 2
                for seg in segs:
                    if self._add_seg_measure(seg):
                        results.append(f"ℓ = {_seg_len(seg):.1f}")

        else:
            # ── n ≥ 3: đo độ dài từng đoạn ──────────────────────────
            # (để đo góc: chọn đúng 2 đoạn rồi Enter)
            for seg in segs:
                if self._add_seg_measure(seg):
                    results.append(f"ℓ = {_seg_len(seg):.1f}")

        # Thông báo kết quả
        if results:
            self.tm.status_hint.emit(
                "✓ " + ";  ".join(results)
                + "   —   click đoạn để chọn tiếp, Esc để huỷ")
        else:
            self.tm.status_hint.emit(
                "Nhãn đã tồn tại   —   click đoạn khác hoặc Esc")

        # Xoá selection sau khi đo
        self._sel      = []
        self._cyc_pos  = None
        self._cyc_segs = []
        self._cyc_last = None
        self.scene.clearSelection()

    # ── Helpers: tìm đoạn ────────────────────────────────────────────────

    def _segs_at(self, pos: QPointF) -> list:
        """Tất cả SegmentItem tại pos, đoạn ngắn trước."""
        view = self.scene.views()[0] if self.scene.views() else None
        t    = view.transform() if view else QTransform()
        result = []
        for item in self.scene.items(
                pos,
                Qt.ItemSelectionMode.IntersectsItemShape,
                Qt.SortOrder.DescendingOrder,
                t):
            if isinstance(item, SegmentItem):
                result.append(item)
        result.sort(key=lambda s: s.length())
        return result

    # ── Helpers: tạo nhãn (không trùng) ─────────────────────────────────

    def _add_seg_measure(self, seg: SegmentItem) -> bool:
        """Trả về True nếu tạo mới."""
        if any(isinstance(it, SegmentMeasureItem) and it.seg is seg
               for it in self.scene.items()):
            return False
        m = SegmentMeasureItem(seg)
        self.scene.addItem(m)
        self.history.push_add(self.scene, m)
        return True

    def _add_angle_measure(self, vertex, arm1, arm2) -> bool:
        """Trả về True nếu tạo mới."""
        for it in self.scene.items():
            if not isinstance(it, AngleMeasureItem):
                continue
            if it.vertex is not vertex:
                continue
            if (it.p1 is arm1 and it.p2 is arm2) or (it.p1 is arm2 and it.p2 is arm1):
                return False
        m = AngleMeasureItem(vertex, arm1, arm2)
        self.scene.addItem(m)
        self.history.push_add(self.scene, m)
        return True

    # ── Gợi ý status bar ─────────────────────────────────────────────────

    def _emit_hint(self):
        self.tm.status_hint.emit(
            "Đo: click chọn đoạn thẳng → Enter để đo   |   Esc: huỷ chọn")

    def _emit_state_hint(self):
        n = len(self._sel)
        if n == 0:
            self._emit_hint()
            return
        if n == 1:
            px = _seg_len(self._sel[0])
            self.tm.status_hint.emit(
                f"1 đoạn ({px:.1f}) — Enter: đo độ dài   |   "
                "click đoạn 2 để chọn góc   |   Esc: huỷ")
        elif n == 2:
            rv = _shared_vertex(*self._sel)
            if rv and not _are_collinear(*rv):
                ang = _angle_at(*rv)
                self.tm.status_hint.emit(
                    f"Góc ≈ {ang:.1f}° — Enter: tạo nhãn góc   |   "
                    "click thêm đoạn   |   Esc: huỷ")
            else:
                self.tm.status_hint.emit(
                    "2 đoạn (không chung đỉnh) — Enter: đo độ dài cả 2   |   Esc: huỷ")
        else:
            self.tm.status_hint.emit(
                f"{n} đoạn được chọn — Enter: đo độ dài tất cả   |   Esc: huỷ")


# ── Pure functions dùng chung (có thể tái sử dụng cho bisector, v.v.) ────────

def _shared_vertex(seg1: SegmentItem, seg2: SegmentItem):
    """
    Nếu seg1 và seg2 chung 1 điểm đầu/cuối:
        trả về (vertex, arm1, arm2)  — arm = điểm còn lại của mỗi đoạn.
    Ngược lại: trả về None.
    """
    if seg1.p1 is seg2.p1:
        return seg1.p1, seg1.p2, seg2.p2
    if seg1.p1 is seg2.p2:
        return seg1.p1, seg1.p2, seg2.p1
    if seg1.p2 is seg2.p1:
        return seg1.p2, seg1.p1, seg2.p2
    if seg1.p2 is seg2.p2:
        return seg1.p2, seg1.p1, seg2.p1
    return None


def _are_collinear(vertex, arm1, arm2) -> bool:
    """True nếu 2 tia (vertex→arm1) và (vertex→arm2) thẳng hàng (góc < 5°)."""
    sv  = vertex.scenePos()
    v1x = arm1.scenePos().x() - sv.x()
    v1y = arm1.scenePos().y() - sv.y()
    v2x = arm2.scenePos().x() - sv.x()
    v2y = arm2.scenePos().y() - sv.y()
    l1  = math.sqrt(v1x * v1x + v1y * v1y)
    l2  = math.sqrt(v2x * v2x + v2y * v2y)
    if l1 < 1e-6 or l2 < 1e-6:
        return True
    return abs(v1x * v2y - v1y * v2x) / (l1 * l2) < _COLLINEAR_SIN


def _seg_len(seg: SegmentItem) -> float:
    sp1, sp2 = seg.p1.scenePos(), seg.p2.scenePos()
    dx = sp2.x() - sp1.x()
    dy = sp2.y() - sp1.y()
    return math.sqrt(dx * dx + dy * dy)


def _angle_at(vertex, arm1, arm2) -> float:
    """Góc (độ) tại vertex giữa 2 tia vertex→arm1 và vertex→arm2."""
    sv  = vertex.scenePos()
    v1x = arm1.scenePos().x() - sv.x()
    v1y = arm1.scenePos().y() - sv.y()
    v2x = arm2.scenePos().x() - sv.x()
    v2y = arm2.scenePos().y() - sv.y()
    l1  = math.sqrt(v1x * v1x + v1y * v1y)
    l2  = math.sqrt(v2x * v2x + v2y * v2y)
    if l1 < 1e-6 or l2 < 1e-6:
        return 0.0
    cos_a = max(-1.0, min(1.0, (v1x * v2x + v1y * v2y) / (l1 * l2)))
    return math.degrees(math.acos(cos_a))
