from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QTransform
from .base_tool import BaseTool

# px manhattan — vùng "cùng vị trí" để nhận ra click lặp lại
_CYCLE_DIST     = 20.0
# px manhattan — ngưỡng tối thiểu để tính là drag thật (lọc jitter bút stylus)
_DRAG_THRESHOLD =  8.0


class SelectTool(BaseTool):
    name = "select"
    _cursor_shape = Qt.CursorShape.ArrowCursor

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._dragging             = False
        self._drag_start_mouse: QPointF = None
        self._drag_start_positions: dict = {}
        self._did_drag             = False   # True khi đã vượt ngưỡng drag

        # ── Trạng thái cycle ──────────────────────────────────────────
        self._cycle_pos:  QPointF = None   # vị trí click lần trước
        self._cycle_items: list   = []     # danh sách đã sắp xếp (để lấy len)
        self._cycle_idx:  int     = 0      # đang chọn item thứ mấy
        self._cycle_last           = None  # item vừa được chọn (identity)

    # ── Lifecycle ─────────────────────────────────────────────────────

    def activate(self):
        self.scene.clearSelection()
        self._reset()

    def deactivate(self):
        self._reset()

    def _reset(self):
        self._dragging             = False
        self._did_drag             = False
        self._drag_start_mouse     = None
        self._drag_start_positions = {}

    def _reset_cycle(self):
        self._cycle_pos   = None
        self._cycle_items = []
        self._cycle_idx   = 0
        self._cycle_last  = None

    # ── Lấy tất cả GeoItem tại pos ───────────────────────────────────

    def _geo_items_at(self, pos: QPointF) -> list:
        """Tất cả GeoItem có thể chọn tại pos (theo thứ tự Z giảm dần)."""
        view = self.scene.views()[0] if self.scene.views() else None
        transform = view.transform() if view else QTransform()
        all_items = self.scene.items(
            pos,
            Qt.ItemSelectionMode.IntersectsItemShape,
            Qt.SortOrder.DescendingOrder,
            transform,
        )
        return [it for it in all_items
                if (it.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                    and hasattr(it, 'color'))]

    # ── Sắp xếp: điểm → đoạn ngắn→dài → item khác ───────────────────

    @staticmethod
    def _sort_key(item):
        from items.point import PointItem
        from items.segment import SegmentItem
        if isinstance(item, PointItem):
            sp = item.scenePos()
            return (0, 0.0, sp.x(), sp.y())
        if isinstance(item, SegmentItem):
            sp1, sp2 = item.p1.scenePos(), item.p2.scenePos()
            mx = (sp1.x() + sp2.x()) / 2
            my = (sp1.y() + sp2.y()) / 2
            return (1, item.length(), mx, my)
        return (2, 0.0, 0.0, item.zValue())

    # ── Logic chọn có cycle ───────────────────────────────────────────

    def _pick(self, pos: QPointF, items: list):
        """
        Trả về item cần chọn theo thứ tự cycle.
        Lần đầu click → item ưu tiên nhất (điểm > đoạn ngắn > dài).
        Click lại cùng chỗ → item tiếp theo trong danh sách (vòng tròn).
        """
        if not items:
            self._reset_cycle()
            return None

        sorted_items = sorted(items, key=self._sort_key)

        same_pos = (
            self._cycle_pos is not None and
            (pos - self._cycle_pos).manhattanLength() <= _CYCLE_DIST
        )

        if same_pos and self._cycle_last is not None and len(sorted_items) > 1:
            # Tìm item vừa chọn lần trước → tiến 1 bước
            try:
                last_idx = next(
                    i for i, it in enumerate(sorted_items)
                    if it is self._cycle_last
                )
                self._cycle_idx = (last_idx + 1) % len(sorted_items)
            except StopIteration:
                self._cycle_idx = 0   # item cũ đã bị xóa → bắt đầu lại
        else:
            self._cycle_idx = 0       # vị trí mới hoặc lần đầu

        self._cycle_pos   = QPointF(pos)
        self._cycle_items = sorted_items
        self._cycle_last  = sorted_items[self._cycle_idx]
        return sorted_items[self._cycle_idx]

    # ── Chọn item (dùng chung cho press và double_click) ─────────────

    def _select_at(self, pos: QPointF, modifiers):
        from items.shape import ShapeItem
        # Ctrl (hoặc Shift) + click → thêm / bớt vào vùng chọn (chọn nhiều)
        from PyQt6.QtWidgets import QApplication
        mods = modifiers | QApplication.keyboardModifiers()   # bút không gửi kèm phím
        shift = bool(mods & (Qt.KeyboardModifier.ShiftModifier |
                             Qt.KeyboardModifier.ControlModifier))
        # Hình mẫu: click 1 lần chỉ chọn cạnh / đỉnh; cả hình → double-click
        items = [it for it in self._geo_items_at(pos)
                 if not (isinstance(it, ShapeItem) and it.edges
                         and not it.isSelected())]

        if not items:
            if not shift:   # Ctrl+click chỗ trống → giữ nguyên vùng chọn
                self.scene.clearSelection()
            self._reset_cycle()
            return False   # không có item

        item = self._pick(pos, items)

        if shift:
            item.setSelected(not item.isSelected())
        else:
            if not item.isSelected():
                self.scene.clearSelection()
            item.setSelected(True)

        n = len(self._cycle_items)
        if n > 1:
            idx  = self._cycle_idx + 1
            name = _item_label(item)
            self.tm.status_hint.emit(
                f"{name}  [{idx}/{n}] — click lại để chọn item tiếp theo")
        else:
            # Kiểm tra nếu có nhiều SegmentItem được chọn → gợi ý D để đo
            self._hint_multiselect()

        return True   # đã chọn item

    # ── Events ────────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return

        found = self._select_at(pos, modifiers)

        if found:
            # Chuẩn bị drag (chưa bắt đầu di chuyển item cho đến khi vượt ngưỡng)
            self._dragging             = True
            self._did_drag             = False
            self._drag_start_mouse     = pos
            # Hình mẫu (ShapeItem) di chuyển bằng cách kéo các đỉnh của nó
            from items.shape import shape_of
            drag_items = []
            for it in self.scene.selectedItems():
                shp = shape_of(it)
                if shp is not None:
                    drag_items.extend(p for p in shp.points
                                      if p not in drag_items)
                elif it not in drag_items:
                    drag_items.append(it)
            self._drag_start_positions = {
                it: QPointF(it.pos()) for it in drag_items
            }
        else:
            self._reset()

    def double_click(self, pos: QPointF):
        """Double-click vào nhãn → sửa font / cỡ chữ; còn lại cycle như single-click."""
        from items.label import LabelItem
        from items.point_label import PointLabelItem
        for it in self._geo_items_at(pos):
            if isinstance(it, (LabelItem, PointLabelItem)):
                self._reset()
                from ui.label_dialog import edit_label
                edit_label(it, self.scene, self.history)
                return
        from items.shape import shape_of
        from items.point import PointItem
        hits = self._geo_items_at(pos)
        if any(isinstance(it, PointItem) for it in hits):
            # Double-click trúng đỉnh → vẫn là chọn / kéo điểm, không chọn cả hình
            self._select_at(pos, Qt.KeyboardModifier.NoModifier)
            return
        for it in hits:
            shp = shape_of(it)
            if shp is not None:
                # Double-click vào hình mẫu (cạnh hoặc bên trong) → chọn cả hình
                self._reset()
                self.scene.clearSelection()
                shp.setSelected(True)
                self.tm.status_hint.emit(
                    f"Đã chọn cả {shp.shape_label} — kéo để di chuyển, "
                    "Delete để xóa")
                return
        self._select_at(pos, Qt.KeyboardModifier.NoModifier)

    def move(self, pos: QPointF, modifiers):
        if not self._dragging or self._drag_start_mouse is None:
            return
        delta = pos - self._drag_start_mouse
        # Chỉ bắt đầu kéo khi vượt ngưỡng (lọc jitter bút stylus)
        if delta.manhattanLength() < _DRAG_THRESHOLD:
            return
        self._did_drag = True
        from items.shape import constraints_suspended
        if len(self._drag_start_positions) > 1:
            # Kéo cả khối → không áp ràng buộc hình mẫu
            with constraints_suspended():
                for item, start_pos in self._drag_start_positions.items():
                    item.setPos(start_pos + delta)
        else:
            for item, start_pos in self._drag_start_positions.items():
                item.setPos(start_pos + delta)

    def release(self, pos: QPointF, button):
        if self._dragging and self._did_drag:
            # Drag thật → lưu lịch sử di chuyển và reset cycle
            self.history.push_move_group(
                [(item, start_pos, QPointF(item.pos()))
                 for item, start_pos in self._drag_start_positions.items()])
            self._reset_cycle()
        self._reset()

    def key_press(self, key, modifiers):
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            from items.shape import expand_for_delete
            selected = expand_for_delete(self.scene.selectedItems())
            if selected:
                self.history.push_remove(self.scene, selected)
                self._reset_cycle()
        elif key == Qt.Key.Key_Escape:
            self.scene.clearSelection()
            self._reset_cycle()
        elif key == Qt.Key.Key_H:
            self._toggle_hidden()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal,
                     Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            # +/− → đổi cỡ chữ các nhãn đang chọn
            from ui.label_dialog import resize_labels
            step = 1 if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal) else -1
            resize_labels(self.scene.selectedItems(), step, self.history)

    def _toggle_hidden(self):
        """
        H với item đang chọn → ẩn/hiện item đó.
        H không có gì được chọn   → hiện tất cả item đang bị ẩn.
        """
        from items.base import GeoItem
        selected = [it for it in self.scene.selectedItems()
                    if isinstance(it, GeoItem)]
        if selected:
            # Nếu còn bất kỳ item nào đang hiện → ẩn tất cả; ngược lại → hiện tất cả
            any_visible = any(not it._is_hidden for it in selected)
            self.history.push_visibility(selected, any_visible)
            state = "ẩn" if any_visible else "hiện"
            self.tm.status_hint.emit(
                f"✓ Đã {state} {len(selected)} đối tượng  (Ctrl+Z để hoàn tác)")
        else:
            # Không có selection → hiện tất cả item đang ẩn
            hidden_items = [it for it in self.scene.items()
                            if isinstance(it, GeoItem) and it._is_hidden]
            if hidden_items:
                self.history.push_visibility(hidden_items, False)
                self.tm.status_hint.emit(
                    f"✓ Đã hiện {len(hidden_items)} đối tượng bị ẩn  (Ctrl+Z để hoàn tác)")
            else:
                self.tm.status_hint.emit("Không có đối tượng nào đang bị ẩn")

    def _hint_multiselect(self):
        """Gợi ý D/J khi có ≥ 1 SegmentItem/RayItem được chọn."""
        from items.segment import SegmentItem
        from items.line import RayItem
        sel_segs = [it for it in self.scene.selectedItems()
                    if isinstance(it, (SegmentItem, RayItem))]
        n = len(sel_segs)
        if n == 0:
            return
        if n == 1:
            self.tm.status_hint.emit(
                f"Đã chọn 1 đoạn — Ctrl+click thêm đoạn khác; D để đo độ dài")
        elif n == 2:
            # Kiểm tra xem 2 đoạn có chung đỉnh không
            from tools.measure_tool import _shared_vertex, _are_collinear
            rv = _shared_vertex(sel_segs[0], sel_segs[1])
            if rv and not _are_collinear(*rv):
                from tools.measure_tool import _angle_at
                ang = _angle_at(*rv)
                self.tm.status_hint.emit(
                    f"Góc ≈ {ang:.1f}° — D: đo góc   |   J: vẽ phân giác   |   Ctrl+click: thêm đoạn")
            else:
                self.tm.status_hint.emit(
                    f"2 đoạn — D: đo độ dài cả 2   |   Ctrl+click: thêm đoạn")
        else:
            self.tm.status_hint.emit(
                f"{n} đoạn được chọn — D: đo độ dài   |   Ctrl+click: thêm/bớt")


# ── Helper: tên gợi nhớ của item ─────────────────────────────────────────────

def _item_label(item) -> str:
    from items.point import PointItem
    from items.segment import SegmentItem
    from items.line import LineItem, RayItem

    if isinstance(item, PointItem):
        return f"Điểm {item.label or '?'}"
    if isinstance(item, SegmentItem):
        a = item.p1.label or "?"
        b = item.p2.label or "?"
        ln = item.length()
        return f"Đoạn {a}{b} ({ln:.1f}px)"
    if isinstance(item, LineItem):
        a = item.p1.label or "?"
        b = item.p2.label or "?"
        return f"Đường thẳng {a}{b}"
    if isinstance(item, RayItem):
        a = item.p1.label or "?"
        b = item.p2.label or "?"
        return f"Tia {a}{b}"
    return type(item).__name__
