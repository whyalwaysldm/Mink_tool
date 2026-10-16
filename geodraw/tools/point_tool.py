from PyQt6.QtCore import Qt, QPointF
from .base_tool import BaseTool
from items.point import PointItem


class PointTool(BaseTool):
    name = "point"

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return
        snapped_item, snapped_pos = self.scene.snap(pos)
        if snapped_item:
            return  # điểm đã tồn tại — không tạo trùng

        pt = PointItem(snapped_pos)
        self.scene.addItem(pt)

        # ── Tự động tạo đoạn từ pt đến các điểm cùng đường/đoạn ──────
        from utils.collinear import auto_segments_for_new_point
        auto_segs = auto_segments_for_new_point(self.scene, pt)

        all_items = [pt] + auto_segs
        if len(all_items) == 1:
            self.history.push_add(self.scene, pt)
        else:
            self.history.push_add_batch(self.scene, all_items)
            n = len(auto_segs)
            self.tm.status_hint.emit(
                f"✓ Tự động nhận diện {n} đoạn thẳng")
