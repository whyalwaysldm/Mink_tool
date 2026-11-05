from PyQt6.QtCore import Qt, QPointF
from .base_tool import BaseTool
from items.circle import CircleItem
from items.circumcircle import CircumcircleItem
from items.arc import ArcItem
from items.on_curve import anchor_points
from items.common_tangent import CommonTangentPointItem, CommonTangentLineItem
from utils.snap_engine import curves_of, _nearest_on_curve

_CIRCLES = (CircleItem, CircumcircleItem, ArcItem)


class CommonTangentTool(BaseTool):
    """
    Tiếp tuyến chung của 2 đường tròn: vẽ mọi tiếp tuyến chung (tối đa 4).

    • Click lần lượt 2 đường tròn, hoặc
    • Ctrl + click 2 đường tròn (công cụ Chọn) rồi bấm X.
    Kéo hình: tiếp tuyến tự cập nhật, tự ẩn / hiện khi số tiếp tuyến chung
    thay đổi (2 đường tròn cắt nhau, tiếp xúc, lồng nhau…).
    """
    name = "common_tangent"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._first = None

    def activate(self):
        self._first = None
        circles = [it for it in self.scene.selectedItems()
                   if isinstance(it, _CIRCLES)]
        if len(circles) == 2:
            self.scene.clearSelection()
            self._create(*circles)
            return
        self.scene.clearSelection()
        self.tm.status_hint.emit(
            "Tiếp tuyến chung: click đường tròn thứ nhất "
            "(hoặc Ctrl + click 2 đường tròn ở công cụ Chọn rồi bấm X)")

    def deactivate(self):
        if self._first is not None and self._first.scene():
            self._first.setSelected(False)
        self._first = None

    def _circle_at(self, pos: QPointF):
        for it in self.scene.items():
            if isinstance(it, _CIRCLES) and it.isVisible():
                for c in curves_of(it):
                    if _nearest_on_curve(pos, c) is not None:
                        return it
        return None

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        circle = self._circle_at(pos)
        if circle is None:
            self.tm.status_hint.emit("Tiếp tuyến chung: hãy click vào một đường tròn")
            return
        if self._first is None:
            self._first = circle
            circle.setSelected(True)
            self.tm.status_hint.emit("Tiếp tuyến chung: click đường tròn thứ hai")
            return
        if circle is self._first:
            return
        first, self._first = self._first, None
        first.setSelected(False)
        self._create(first, circle)

    def _create(self, c1, c2):
        anchors = anchor_points(self.scene, c1)
        anchors += [p for p in anchor_points(self.scene, c2) if p not in anchors]
        items, shown = [], 0
        for s in (1, -1):
            for side in (1, -1):
                t1 = CommonTangentPointItem(c1, c2, s, side, 0, anchors)
                t2 = CommonTangentPointItem(c1, c2, s, side, 1, anchors)
                items += [t1, t2, CommonTangentLineItem(t1, t2)]
                shown += t1.exists
        self.history.push_add_batch(self.scene, items)
        self.tm.status_hint.emit(
            f"✓ Đã vẽ {shown} tiếp tuyến chung — kéo 2 đường tròn, số tiếp "
            "tuyến tự thay đổi theo vị trí" if shown else
            "Hiện 2 đường tròn không có tiếp tuyến chung — kéo ra xa nhau "
            "để tiếp tuyến hiện ra")

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Escape:
            self.deactivate()
            self.activate()
