import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem


def _circumcenter(A: QPointF, B: QPointF, C: QPointF):
    ax, ay = A.x(), A.y()
    bx, by = B.x(), B.y()
    cx, cy = C.x(), C.y()
    D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
    if abs(D) < 1e-10:
        return None, 0.0
    ux = ((ax*ax + ay*ay) * (by - cy) + (bx*bx + by*by) * (cy - ay) +
          (cx*cx + cy*cy) * (ay - by)) / D
    uy = ((ax*ax + ay*ay) * (cx - bx) + (bx*bx + by*by) * (ax - cx) +
          (cx*cx + cy*cy) * (bx - ax)) / D
    r = math.sqrt((ax - ux)**2 + (ay - uy)**2)
    return QPointF(ux, uy), r


class CircumcenterItem(PointItem):
    """Center point of circumcircle, constrained to circumcenter of 3 points."""
    is_constrained = True

    def __init__(self, p1: PointItem, p2: PointItem, p3: PointItem, color=None):
        self._updating = False
        self._p1, self._p2, self._p3 = p1, p2, p3
        super().__init__(QPointF(0, 0), color)
        p1.add_dependent(self)
        p2.add_dependent(self)
        p3.add_dependent(self)
        self.update_position()

    def _compute_pos(self):
        center, _ = _circumcenter(
            self._p1.scenePos(), self._p2.scenePos(), self._p3.scenePos())
        return center

    def update_position(self):
        pos = self._compute_pos()
        if pos is not None:
            self._updating = True
            self.setPos(pos)
            self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        return super().itemChange(change, value)

    def remove_from_scene(self):
        self._p1.remove_dependent(self)
        self._p2.remove_dependent(self)
        self._p3.remove_dependent(self)


class CircumcircleItem(GeoItem):
    """Circle passing through 3 PointItems."""

    def __init__(self, p1: PointItem, p2: PointItem, p3: PointItem,
                 color=None, width=None):
        super().__init__(color, width)
        self._p1, self._p2, self._p3 = p1, p2, p3
        p1.add_dependent(self)
        p2.add_dependent(self)
        p3.add_dependent(self)
        self.setZValue(1)

    def remove_from_scene(self):
        self._p1.remove_dependent(self)
        self._p2.remove_dependent(self)
        self._p3.remove_dependent(self)

    def _data(self):
        return _circumcenter(
            self._p1.scenePos(), self._p2.scenePos(), self._p3.scenePos())

    def boundingRect(self) -> QRectF:
        center, r = self._data()
        if center is None:
            return QRectF(-1, -1, 2, 2)
        lc = self.mapFromScene(center)
        pad = r + self.stroke_width + 4
        return QRectF(lc.x() - pad, lc.y() - pad, pad * 2, pad * 2)

    def paint(self, painter: QPainter, option, widget=None):
        center, r = self._data()
        if center is None or r < 0.5:
            return
        lc = self.mapFromScene(center)
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawEllipse(lc, r, r)
