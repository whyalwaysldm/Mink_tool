"""
ShapeItem — hình mẫu (hình vuông, tam giác đều…) dựng từ các điểm đỉnh.

• Mỗi đỉnh là một PointItem → kéo được, bắt dính được như điểm thường.
• Kéo 1 đỉnh: tùy loại hình (xem _solve). Mặc định cả hình co giãn + xoay
  quanh đỉnh đối diện (phép đồng dạng) nên hình dạng giữ nguyên; hình chữ
  nhật, hình thoi, tam giác vuông/cân, hình bình hành, hình thang có quy tắc
  riêng để đổi tỉ lệ mà vẫn đúng loại hình.
• Kéo cạnh (SelectTool) → di chuyển cả hình.
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


def _dot(a: QPointF, b: QPointF) -> float:
    return a.x() * b.x() + a.y() * b.y()


def _cross(a: QPointF, b: QPointF) -> float:
    return a.x() * b.y() - a.y() * b.x()


def _unit(v: QPointF) -> QPointF:
    L = (v.x() ** 2 + v.y() ** 2) ** 0.5
    return QPointF(v.x() / L, v.y() / L) if L > 1e-9 else QPointF(1, 0)


def _keep_sign(val: float, ref: float, min_abs: float = 4.0) -> float:
    """Giữ cùng dấu với ref và |val| ≥ min_abs (không cho hình bị lật / dẹt)."""
    sign = 1.0 if ref >= 0 else -1.0
    return sign * max(min_abs, val * sign)


def _solve(kind: str, i: int, L: list, m: QPointF):
    """
    Quy tắc kéo đỉnh i tới m cho từng loại hình (L = vị trí cũ các đỉnh).
    Trả về vị trí mới của mọi đỉnh, hoặc None → dùng phép đồng dạng
    (co giãn + xoay quanh đỉnh đối diện, giữ nguyên hình dạng).
    """
    n = len(L)
    if kind == "rectangle":
        # Đỉnh đối diện đứng yên, 2 trục giữ nguyên → đổi dài / rộng tự do
        j = (i + 2) % 4
        P = L[j]
        u = _unit(L[1] - L[0])
        v = _unit(L[3] - L[0])
        a0, b0 = _dot(L[i] - P, u), _dot(L[i] - P, v)
        a = _keep_sign(_dot(m - P, u), a0)
        b = _keep_sign(_dot(m - P, v), b0)
        out = list(L)
        out[i] = P + u * a + v * b
        for k in ((i + 1) % 4, (i + 3) % 4):
            o = L[k] - P
            out[k] = P + u * a if abs(_dot(o, u)) > abs(_dot(o, v)) else P + v * b
        return out

    if kind == "rhombus":
        # Tâm + 2 trục giữ nguyên, cạnh giữ nguyên độ dài → co giãn đường chéo
        j = (i + 2) % 4
        c = (L[i] + L[j]) / 2
        e = _unit(L[i] - c)
        f = _unit(L[(i + 1) % 4] - c)
        side = ((L[i] - L[(i + 1) % 4]).x() ** 2 +
                (L[i] - L[(i + 1) % 4]).y() ** 2) ** 0.5
        t = max(0.08 * side, min(0.92 * side, _dot(m - c, e)))
        q = (side * side - t * t) ** 0.5
        out = list(L)
        out[i] = c + e * t
        out[j] = c - e * t
        out[(i + 1) % 4] = c + f * q
        out[(i + 3) % 4] = c - f * q
        return out

    if kind == "right_triangle" and i in (1, 2):
        # Góc vuông tại đỉnh 0: đỉnh 1/2 trượt trên cạnh góc vuông của nó
        u = _unit(L[i] - L[0])
        out = list(L)
        out[i] = L[0] + u * max(4.0, _dot(m - L[0], u))
        return out

    if kind == "isosceles_triangle" and i == 0:
        # Đỉnh cân trượt trên đường cao → đổi chiều cao, đáy giữ nguyên
        mid = (L[1] + L[2]) / 2
        e = _unit(L[0] - mid)
        out = list(L)
        out[0] = mid + e * max(4.0, _dot(m - mid, e))
        return out

    if kind == "parallelogram" and i in (2, 3):
        # Đáy 0-1 giữ nguyên; cạnh bên đổi hướng / độ dài tự do
        base = L[1] - L[0]
        w = m - (L[1] if i == 2 else L[0])
        if _cross(base, w) * _cross(base, L[3] - L[0]) <= 0 or \
                abs(_cross(_unit(base), w)) < 4.0:
            return list(L)            # không cho hình bị lật / dẹt
        out = list(L)
        out[2] = L[1] + w
        out[3] = L[0] + w
        return out

    if kind == "trapezoid" and i in (2, 3):
        # Đáy lớn giữ nguyên; đáy nhỏ tịnh tiến (đổi chiều cao / độ lệch)
        base = L[1] - L[0]
        d = m - L[i]
        new_top = L[3] + d
        if _cross(base, new_top - L[0]) * _cross(base, L[3] - L[0]) <= 0 or \
                abs(_cross(_unit(base), new_top - L[0])) < 4.0:
            return list(L)
        out = list(L)
        out[2] = L[2] + d
        out[3] = L[3] + d
        return out

    return None


class ShapeItem(GeoItem):

    def __init__(self, points: list, shape_label: str = "Hình",
                 color=None, width=None, fill_color=None,
                 kind: str = "", edges=None):
        super().__init__(color, width)
        self.points: list = list(points)
        # Cạnh k = SegmentItem(đỉnh k, đỉnh k+1) — click 1 lần chọn cạnh,
        # double-click mới chọn cả hình
        self.edges: list = list(edges or [])
        for k, seg in enumerate(self.edges):
            seg._shape = self
            seg._shape_edge = k
        self.shape_label = shape_label
        # Loại hình (tên tool: rectangle, rhombus…) → quy tắc kéo đỉnh riêng
        self.kind = kind
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
        solved = _solve(self.kind, i, self._last, cur[i])
        if solved is not None:
            self._updating = True
            try:
                for k, p in enumerate(self.points):
                    if (p.scenePos() - solved[k]).manhattanLength() > 1e-9:
                        p.setPos(solved[k])
            finally:
                self._updating = False
            self.sync()
            return
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
