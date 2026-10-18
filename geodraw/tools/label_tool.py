from PyQt6.QtCore import Qt, QPointF
from .base_tool import BaseTool
from items.label import LabelItem
from items.point_label import PointLabelItem

# px manhattan — ngưỡng để tính là kéo thật (lọc rung bút)
_DRAG_THRESHOLD = 4.0


class LabelTool(BaseTool):
    """
    Click → đặt nhãn tự động A, B, C… (click vào điểm → đặt tên cho điểm).
    Kéo nhãn có sẵn → di chuyển nhãn.
    Double-click nhãn → sửa nội dung / font / cỡ chữ.
    + / − → tăng / giảm cỡ chữ nhãn đang chọn.
    """
    name = "label"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._reset()

    def _reset(self):
        self._drag_item = None
        self._drag_start_mouse: QPointF = None
        self._drag_start_pos: QPointF = None
        self._did_drag = False

    def activate(self):
        self._reset()
        self.tm.status_hint.emit(
            "Nhãn: click để đặt A, B, C…  |  kéo nhãn để di chuyển  |  "
            "double-click để đổi tên / font / cỡ chữ  |  +/− đổi cỡ chữ")

    def deactivate(self):
        self._reset()

    def _label_at(self, pos: QPointF):
        for it in self.scene.items(pos):
            if isinstance(it, (LabelItem, PointLabelItem)):
                return it
            parent = it.parentItem()
            if isinstance(parent, LabelItem):
                return parent
        return None

    # ── Events ────────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return
        item = self._label_at(pos)
        if item is not None:
            self.scene.clearSelection()
            item.setSelected(True)
            self._drag_item = item
            self._drag_start_mouse = QPointF(pos)
            self._drag_start_pos = QPointF(item.pos())
            self._did_drag = False
            return
        self.scene.clearSelection()
        self._create_label(pos)

    def move(self, pos: QPointF, modifiers):
        if self._drag_item is None:
            return
        delta = pos - self._drag_start_mouse
        if not self._did_drag and delta.manhattanLength() < _DRAG_THRESHOLD:
            return
        self._did_drag = True
        self._drag_item.setPos(self._drag_start_pos + delta)

    def release(self, pos: QPointF, button):
        if self._drag_item is not None and self._did_drag:
            self.history.push_move(
                self._drag_item, self._drag_start_pos, self._drag_item.pos())
        self._reset()

    def double_click(self, pos: QPointF):
        item = self._label_at(pos)
        if item is not None:
            self._reset()
            from ui.label_dialog import edit_label
            edit_label(item, self.scene, self.history)

    def key_press(self, key, modifiers):
        step = _size_step(key)
        if step:
            from ui.label_dialog import resize_labels
            resize_labels(self.scene.selectedItems(), step, self.history)
            return
        if key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            selected = self.scene.selectedItems()
            if selected:
                self.history.push_remove(self.scene, selected)
            return
        super().key_press(key, modifiers)

    # ── Đặt nhãn mới: tự đánh A, B, C… ──────────────────────────────

    def _next_name(self) -> str:
        """Tên chưa dùng tiếp theo: A…Z, rồi A1…Z1, A2…"""
        used = {pt.label for pt in self.scene.point_items() if pt.label}
        used |= {it.text for it in self.scene.items()
                 if isinstance(it, LabelItem)}
        n = 0
        while True:
            suffix = str(n) if n else ""
            for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
                if c + suffix not in used:
                    return c + suffix
            n += 1

    def _create_label(self, pos: QPointF):
        from items.point import PointItem
        name = self._next_name()
        snapped_item, _ = self.scene.snap(pos)
        if isinstance(snapped_item, PointItem):
            point = snapped_item
            if point._label_item is not None:
                self.tm.status_hint.emit(
                    f"Điểm đã có tên '{point.label}' — double-click nhãn để đổi")
                return
            point.label = name
            item = PointLabelItem(point, name)
        else:
            item = LabelItem(name, pos)
        self.scene.addItem(item)
        self.history.push_add(self.scene, item)
        self.tm.status_hint.emit(
            f"✓ Đã đặt nhãn '{name}'  —  double-click để đổi tên / font / cỡ chữ")


def _size_step(key) -> int:
    """+ / = → +1 ;  − / _ → −1 ; khác → 0."""
    if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
        return 1
    if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
        return -1
    return 0
