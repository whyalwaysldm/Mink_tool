from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QDialog
from .base_tool import BaseTool
from items.label import LabelItem
from items.point_label import PointLabelItem

# px manhattan — ngưỡng để tính là kéo thật (lọc rung bút)
_DRAG_THRESHOLD = 4.0


class LabelTool(BaseTool):
    """
    Click chỗ trống → tạo nhãn mới (chọn nội dung, font, cỡ chữ).
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
            "Nhãn: click chỗ trống để tạo  |  kéo nhãn để di chuyển  |  "
            "double-click để đổi font / cỡ chữ  |  +/− đổi cỡ chữ")

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

    # ── Tạo nhãn mới ──────────────────────────────────────────────────

    def _create_label(self, pos: QPointF):
        from config.app_settings import AppSettings
        from ui.label_dialog import LabelDialog, remember_label_font
        s = AppSettings.load()
        view = self.scene.views()[0] if self.scene.views() else None
        dlg = LabelDialog(view, "Nhập nhãn", "",
                          s.label_font_family, s.label_font_size)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        text, family, size = dlg.values()
        if not text:
            return
        remember_label_font(family, size)
        lbl = LabelItem(text, pos, font_size=size, font_family=family)
        self.scene.addItem(lbl)
        self.history.push_add(self.scene, lbl)


def _size_step(key) -> int:
    """+ / = → +1 ;  − / _ → −1 ; khác → 0."""
    if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
        return 1
    if key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
        return -1
    return 0
