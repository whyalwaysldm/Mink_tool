"""
ShapeItem — hình mẫu (hình vuông, tam giác đều…) dựng từ các điểm đỉnh.

• Mỗi đỉnh là một PointItem → kéo được, bắt dính được như điểm thường.
• Kéo 1 đỉnh: cả hình co giãn + xoay quanh đỉnh đối diện (phép đồng dạng),
  nên hình dạng luôn giữ nguyên (vuông vẫn vuông, đều vẫn đều…).
• Kéo thân hình (SelectTool) → di chuyển tất cả đỉnh cùng lúc.
"""
from contextlib import contextmanager
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF, QPainterPath
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem

# Khi > 0: tạm tắt ràng buộc (di chuyển cả khối, undo/redo nhóm)
_suspend_depth = 0


@contextmanager
def constraints_suspended():
    global _suspend_depth
    _suspend_depth += 1
    try:
        yield
    finally:
        _suspend_depth -= 1


class ShapeItem(GeoItem):

    def __init__(self, points: list, shape_label: str = "Hình",
                 color=None, width=None, fill_color=None):
        super().__init__(color, width)
        self.points: list = list(points)
        self.shape_label = shape_label
        self.fill_color: QColor = fill_color or QColor(200, 220, 255, 50)
        self._updating = False
        self._last: list = []
        for p in self.points:
            p.add_dependent(self)
        self.sync()
        self.setZValue(1)

    # ── Ràng buộc ─────────────────────────────────────────────────────────

    def sync(self):
        """Ghi nhớ vị trí hiện tại của các đỉnh."""
        self._last = [QPointF(p.scenePos()) for p in self.points]

    def update_position(self):
        """Gọi bởi PointItem khi một đỉnh di chuyển."""
        if self._updating:
            return
        n = len(self.points)
        if _suspend_depth or len(self._last) != n:
            self.sync()
            return
        cur = [p.scenePos() for p in self.points]
        moved = [i for i in range(n)
                 if (cur[i] - self._last[i]).manhattanLength() > 1e-6]
        if len(moved) != 1:
            self.sync()
            return
        i = moved[0]
        j = (i + n // 2) % n          # đỉnh đối diện làm tâm
        pivot = self._last[j]
        old_v = self._last[i] - pivot
        new_v = cur[i] - pivot
        d = old_v.x() ** 2 + old_v.y() ** 2
        if d < 1e-9 or (new_v.x() ** 2 + new_v.y() ** 2) < 4.0:
            # Kéo trùng vào tâm → không hợp lệ, trả đỉnh về chỗ cũ
            self._updating = True
            self.points[i].setPos(self._last[i])
            self._updating = False
            return
        # Phép đồng dạng z → pivot + k·(z − pivot), k = new_v / old_v (số phức)
        a = (new_v.x() * old_v.x() + new_v.y() * old_v.y()) / d
        b = (new_v.y() * old_v.x() - new_v.x() * old_v.y()) / d
        self._updating = True
        try:
            for k, p in enumerate(self.points):
                if k == i:
                    continue
                v = self._last[k] - pivot
                p.setPos(QPointF(pivot.x() + a * v.x() - b * v.y(),
                                 pivot.y() + b * v.x() + a * v.y()))
        finally:
            self._updating = False
        self.sync()

    # ── Thêm / xóa khỏi scene ─────────────────────────────────────────────

    def remove_from_scene(self):
        for p in self.points:
            p.remove_dependent(self)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene() is not None:
                # Khôi phục liên kết sau undo xóa
                for p in self.points:
                    p.add_dependent(self)
                self.sync()
        return super().itemChange(change, value)

    # ── Vẽ ───────────────────────────────────────────────────────────────

    def _local_poly(self) -> QPolygonF:
        return QPolygonF([self.mapFromScene(p.scenePos()) for p in self.points])

    def boundingRect(self) -> QRectF:
        poly = self._local_poly()
        if poly.isEmpty():
            return QRectF()
        pad = self.stroke_width + 4
        return poly.boundingRect().adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addPolygon(self._local_poly())
        path.closeSubpath()
        return path

    def paint(self, painter: QPainter, option, widget=None):
        poly = self._local_poly()
        if poly.count() < 2:
            return
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.fill_color))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPolygon(poly)
