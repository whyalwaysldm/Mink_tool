from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QInputDialog
from .base_tool import BaseTool
from items.point import PointItem
from items.point_label import PointLabelItem


class RenamePointTool(BaseTool):
    """
    Click vào điểm → đặt / đổi tên.
    Tên được lưu trong PointLabelItem (kéo được) thay vì vẽ cố định trên điểm.
    """
    name = "rename_point"
    _cursor_shape = Qt.CursorShape.PointingHandCursor

    def activate(self):
        self.tm.status_hint.emit(
            "Đặt tên điểm: click vào điểm cần đặt / đổi tên")

    # ── Helpers ───────────────────────────────────────────────────────────

    def _next_label(self) -> str:
        """Gợi ý chữ cái tiếp theo chưa được dùng."""
        used = {pt.label for pt in self.scene.point_items() if pt.label}
        for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            if c not in used:
                return c
        return ""

    def _label_item_of(self, point: PointItem):
        """Tìm PointLabelItem gắn với point (nếu có)."""
        for it in self.scene.items():
            if isinstance(it, PointLabelItem) and it._point is point:
                return it
        return None

    # ── Event ─────────────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return

        snapped_item, _ = self.scene.snap(pos)
        if not isinstance(snapped_item, PointItem):
            self.tm.status_hint.emit(
                "Đặt tên điểm: hãy click đúng vào một điểm")
            return

        point = snapped_item
        existing = self._label_item_of(point)

        # Mở dialog
        parent_widget = self.scene.views()[0] if self.scene.views() else None
        suggestion = point.label or self._next_label()
        text, ok = QInputDialog.getText(
            parent_widget,
            "Đặt tên điểm",
            "Nhập tên điểm (bỏ trống để xóa nhãn):",
            text=suggestion,
        )
        if not ok:
            return

        name = text.strip()

        # ── Xóa nhãn ──────────────────────────────────────────────────
        if not name:
            if existing is not None:
                self.history.push_remove(self.scene, [existing])
            point.label = ""
            self.tm.status_hint.emit("✓ Đã xóa tên điểm")
            return

        # ── Cập nhật nhãn đã có ───────────────────────────────────────
        if existing is not None:
            existing.text = name          # setter cập nhật point.label
            self.tm.status_hint.emit(f"✓ Đổi tên điểm thành '{name}'")
            return

        # ── Tạo nhãn mới ──────────────────────────────────────────────
        point.label = name
        label_item  = PointLabelItem(point, name)
        self.scene.addItem(label_item)
        self.history.push_add(self.scene, label_item)
        self.tm.status_hint.emit(
            f"✓ Đặt tên điểm: '{name}'  (kéo nhãn để di chuyển)")
