"""
PointOnCurveItem — điểm lấy trên một đường (đoạn, đường thẳng, tia, đường tròn,
cạnh đa giác…).

• Kéo điểm → chỉ trượt trên đường đó (chiếu vuông góc lên đường).
• Đường di chuyển / co giãn → điểm giữ nguyên vị trí tương đối (tham số t
  trên đoạn/đường/tia, góc trên đường tròn) và đi theo.
• Các đối tượng dựng từ điểm này (đoạn, đường vuông góc…) là dependent của
  điểm nên cập nhật theo như với điểm thường.
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QPointF
from .point import PointItem


def anchor_points(scene, host) -> list:
    """Các PointItem mà host phụ thuộc (host nằm trong _dependents của chúng)."""
    if scene is None:
        return []
    return [p for p in scene.items()
            if isinstance(p, PointItem) and host in p._dependents]


def _param_of(curve: tuple, pos: QPointF) -> float:
    t = curve[0]
    if t == 'circle':
        c = curve[1]
        return math.atan2(pos.y() - c.y(), pos.x() - c.x())
    a, b = curve[1], curve[2]
    dx, dy = b.x() - a.x(), b.y() - a.y()
    len_sq = dx * dx + dy * dy
    if len_sq < 1e-12:
        return 0.0
    u = ((pos.x() - a.x()) * dx + (pos.y() - a.y()) * dy) / len_sq
    if t == 'segment':
        u = max(0.0, min(1.0, u))
    elif t == 'ray':
        u = max(0.0, u)
    return u


def _pos_of(curve: tuple, param: float) -> QPointF:
    if curve[0] == 'circle':
        c, r = curve[1], curve[2]
        return QPointF(c.x() + r * math.cos(param), c.y() + r * math.sin(param))
    a, b = curve[1], curve[2]
    return QPointF(a.x() + param * (b.x() - a.x()),
                   a.y() + param * (b.y() - a.y()))


class PointOnCurveItem(PointItem):
    """Điểm gắn trên host (curve thứ index trong curves_of(host))."""
    is_on_curve = True

    def __init__(self, host, index: int, pos: QPointF, anchors: list, color=None):
        self._updating = True
        self._host = host
        self._index = index
        self._anchors = list(anchors)
        self._param = 0.0
        super().__init__(pos, color)
        curve = self._curve()
        if curve is not None:
            self._param = _param_of(curve, pos)
        self._updating = False
        for p in self._anchors:
            p.add_dependent(self)
        self.update_position()

    @property
    def host(self):
        return self._host

    def _curve(self):
        # Đường đã bị xóa (đường phụ) vẫn tính theo các điểm của nó → điểm
        # vẫn giữ đúng tính chất dựng hình
        from utils.snap_engine import curves_of
        curves = curves_of(self._host)
        return curves[self._index] if self._index < len(curves) else None

    def update_position(self):
        """Gọi khi đường di chuyển: đặt lại điểm theo tham số đã lưu."""
        curve = self._curve()
        if curve is None:
            return
        self._updating = True
        self.setPos(_pos_of(curve, self._param))
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            curve = self._curve()
            if curve is not None:
                # Kéo điểm → chiếu lên đường, ghi nhớ tham số mới
                self._param = _param_of(curve, value)
                return _pos_of(curve, self._param)
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for p in self._anchors:
                p.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for p in self._anchors:
            p.remove_dependent(self)


class IntersectionPointItem(PointItem):
    """
    Giao điểm của 2 đường (curve k1 của host1, curve k2 của host2).
    Không kéo trực tiếp được; tự cập nhật khi một trong hai đường di chuyển.
    Đường tròn cắt đường cho 2 giao điểm → giữ giao điểm gần vị trí cũ nhất.
    Giao điểm ra ngoài đoạn / tia → vẫn bám theo phần kéo dài của chúng.
    """
    is_constrained = True

    def __init__(self, host1, k1: int, host2, k2: int, pos: QPointF,
                 anchors: list, color=None):
        self._updating = True         # cho phép đặt vị trí ban đầu = pos
        self._hosts = ((host1, k1), (host2, k2))
        self._anchors = list(anchors)
        super().__init__(pos, color)
        self._updating = False
        for p in self._anchors:
            p.add_dependent(self)
        self.update_position()

    def _compute_pos(self):
        from utils.snap_engine import curves_of, intersect_curves
        cs = []
        for host, k in self._hosts:
            # host bị xóa (đường phụ đã dựng xong) vẫn dùng được: hình học của
            # nó chỉ phụ thuộc các điểm, nên giao điểm vẫn đúng khi kéo hình
            curves = curves_of(host)
            if k >= len(curves):
                return None
            cs.append(curves[k])
        pts = intersect_curves(cs[0], cs[1]) or \
            intersect_curves(cs[0], cs[1], extend=True)
        if not pts:
            return None               # 2 đường không còn cắt nhau → giữ chỗ cũ
        cur = self.scenePos()
        return min(pts, key=lambda q: (q.x() - cur.x()) ** 2 + (q.y() - cur.y()) ** 2)

    def update_position(self):
        pos = self._compute_pos()
        if pos is None:
            return
        self._updating = True
        self.setPos(pos)
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for p in self._anchors:
                p.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for p in self._anchors:
            p.remove_dependent(self)
