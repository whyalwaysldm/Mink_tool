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
                 color=None, width=None, fill_color=None,
                 stretch_edges=(), edges=None):
        super().__init__(color, width)
        self.points: list = list(points)
        # Cạnh k = SegmentItem(đỉnh k, đỉnh k+1) — click 1 lần chọn cạnh,
        # double-click mới chọn cả hình
        self.edges: list = list(edges or [])
        for k, seg in enumerate(self.edges):
            seg._shape = self
            seg._shape_edge = k
        self.shape_label = shape_label
        # Cạnh k = (đỉnh k, đỉnh k+1) có thể kéo dãn theo pháp tuyến mà
        # hình vẫn đúng loại (vd. hình chữ nhật: cả 4 cạnh)
        self.stretch_edges = tuple(stretch_edges)
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

    def stretch_edge_at(self, pos: QPointF, tol: float):
        """Cạnh kéo dãn được gần pos (không tính vùng sát đỉnh), hoặc None."""
        n = len(self.points)
        for k in self.stretch_edges:
            a = self.points[k].scenePos()
            b = self.points[(k + 1) % n].scenePos()
            ab = b - a
            L2 = ab.x() ** 2 + ab.y() ** 2
            if L2 < 1e-9:
                continue
            t = ((pos - a).x() * ab.x() + (pos - a).y() * ab.y()) / L2
            L = L2 ** 0.5
            if t * L < tol * 1.5 or (1 - t) * L < tol * 1.5:
                continue          # sát đỉnh → để kéo đỉnh
            proj = a + ab * t
            d = ((pos - proj).x() ** 2 + (pos - proj).y() ** 2) ** 0.5
            if d <= tol:
                return k
        return None

    def edge_normal(self, k: int) -> QPointF:
        """Pháp tuyến đơn vị của cạnh k, hướng ra ngoài hình."""
        n = len(self.points)
        a = self.points[k].scenePos()
        b = self.points[(k + 1) % n].scenePos()
        ab = b - a
        L = (ab.x() ** 2 + ab.y() ** 2) ** 0.5 or 1.0
        nx, ny = -ab.y() / L, ab.x() / L
        cx = sum(p.scenePos().x() for p in self.points) / n
        cy = sum(p.scenePos().y() for p in self.points) / n
        if (a.x() - cx) * nx + (a.y() - cy) * ny < 0:
            nx, ny = -nx, -ny
        return QPointF(nx, ny)

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
        if self.edges and not self.isSelected():
            # Cạnh do các SegmentItem tự vẽ → ở đây chỉ tô nền
            painter.setPen(Qt.PenStyle.NoPen)
        else:
            color = QColor(0, 120, 215) if self.isSelected() else self.color
            pen = QPen(color, self.stroke_width)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
        painter.setBrush(QBrush(self.fill_color))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPolygon(poly)


def shape_of(item):
    """ShapeItem chứa item (chính nó, hoặc cạnh của nó), hoặc None."""
    if isinstance(item, ShapeItem):
        return item
    return getattr(item, "_shape", None)


def expand_for_delete(items: list) -> list:
    """Xóa cả hình mẫu → xóa luôn cạnh và đỉnh không còn dùng ở chỗ khác."""
    result = list(items)
    for it in items:
        if not isinstance(it, ShapeItem):
            continue
        own = set(it.edges) | {it}
        for seg in it.edges:
            if seg not in result:
                result.append(seg)
        for p in it.points:
            if p in result:
                continue
            if all(d in own for d in p._dependents):
                result.append(p)
    return result
