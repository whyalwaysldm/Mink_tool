"""
Điểm dựng hình phụ thuộc vào một điểm A và một đường (p1, p2):

• FootPointItem      — chân đường vuông góc hạ từ A xuống đường (hiện ra).
• DirectionPointItem — điểm ẩn A + hướng (song song / vuông góc với đường),
  dùng làm điểm thứ hai cho LineItem đi qua A.
• RadiusPointItem    — điểm ẩn cách A bằng độ dài đoạn, làm bán kính đường tròn.

Các điểm này tự cập nhật khi A hoặc đường di chuyển, và không kéo trực tiếp được.
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QPointF
from .point import PointItem

DIRECTION_LEN = 100.0   # px — khoảng cách từ A tới điểm ẩn chỉ hướng


class _ConstrainedPoint(PointItem):
    is_constrained = True

    def __init__(self, a: PointItem, l1: PointItem, l2: PointItem, color=None):
        self._updating = False
        self._a, self._l1, self._l2 = a, l1, l2
        super().__init__(QPointF(0, 0), color)
        for p in (a, l1, l2):
            p.add_dependent(self)
        self.update_position()

    def _dir(self) -> tuple:
        """Vector đơn vị của đường (l1 → l2)."""
        p, q = self._l1.scenePos(), self._l2.scenePos()
        dx, dy = q.x() - p.x(), q.y() - p.y()
        L = math.hypot(dx, dy) or 1.0
        return dx / L, dy / L

    def _compute_pos(self) -> QPointF:
        raise NotImplementedError

    def update_position(self):
        self._updating = True
        self.setPos(self._compute_pos())
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for p in (self._a, self._l1, self._l2):
                p.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for p in (self._a, self._l1, self._l2):
            p.remove_dependent(self)


class FootPointItem(_ConstrainedPoint):
    """Chân đường vuông góc hạ từ A xuống đường (l1, l2)."""

    def _compute_pos(self) -> QPointF:
        ux, uy = self._dir()
        p, a = self._l1.scenePos(), self._a.scenePos()
        t = (a.x() - p.x()) * ux + (a.y() - p.y()) * uy
        return QPointF(p.x() + ux * t, p.y() + uy * t)


class DirectionPointItem(_ConstrainedPoint):
    """Điểm ẩn: A + hướng song song (perpendicular=False) hoặc vuông góc."""

    def __init__(self, a, l1, l2, perpendicular: bool, color=None):
        self._perp = perpendicular
        super().__init__(a, l1, l2, color)
        self.setVisible(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def _compute_pos(self) -> QPointF:
        ux, uy = self._dir()
        if self._perp:
            ux, uy = -uy, ux
        a = self._a.scenePos()
        return QPointF(a.x() + ux * DIRECTION_LEN, a.y() + uy * DIRECTION_LEN)


class RadiusPointItem(_ConstrainedPoint):
    """Điểm ẩn cách tâm A đúng bằng độ dài đoạn (l1, l2) — bán kính cho CircleItem."""

    def __init__(self, a, l1, l2, color=None):
        super().__init__(a, l1, l2, color)
        self.setVisible(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)

    def _compute_pos(self) -> QPointF:
        p, q = self._l1.scenePos(), self._l2.scenePos()
        r = math.hypot(q.x() - p.x(), q.y() - p.y())
        a = self._a.scenePos()
        return QPointF(a.x() + r, a.y())
