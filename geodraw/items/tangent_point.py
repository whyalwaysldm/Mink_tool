"""
TangentPointItem — tiếp điểm của tiếp tuyến kẻ từ điểm P (ngoài đường tròn)
tới đường tròn. side = +1 / −1 chọn 1 trong 2 tiếp điểm.
Tự cập nhật khi P, tâm hoặc bán kính đổi; không kéo trực tiếp được.
P lọt vào trong đường tròn → không có tiếp tuyến, tiếp điểm giữ chỗ cũ.
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QPointF
from .point import PointItem


def tangent_point(p: QPointF, circle: tuple, side: int):
    """Tiếp điểm (QPointF) hoặc None nếu p không nằm ngoài đường tròn."""
    c, r = circle[1], circle[2]
    dx, dy = p.x() - c.x(), p.y() - c.y()
    d = math.hypot(dx, dy)
    if d <= r + 1e-6:
        return None
    a = side * math.acos(r / d)
    ux, uy = dx / d, dy / d
    cs, sn = math.cos(a), math.sin(a)
    return QPointF(c.x() + r * (ux * cs - uy * sn),
                   c.y() + r * (ux * sn + uy * cs))


class TangentPointItem(PointItem):
    is_constrained = True

    def __init__(self, p: PointItem, circle, side: int, anchors: list, color=None):
        self._updating = False
        self._p, self._circle, self._side = p, circle, side
        self._anchors = list(anchors)
        if p not in self._anchors:
            self._anchors.append(p)
        super().__init__(QPointF(0, 0), color)
        for a in self._anchors:
            a.add_dependent(self)
        self.update_position()

    def update_position(self):
        from utils.snap_engine import curves_of
        curves = curves_of(self._circle)
        if not curves:
            return
        t = tangent_point(self._p.scenePos(), curves[0], self._side)
        if t is None:
            return
        self._updating = True
        self.setPos(t)
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for a in self._anchors:
                a.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for a in self._anchors:
            a.remove_dependent(self)
