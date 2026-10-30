import math
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPainterPath
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem, stroke_shape
from .point import PointItem


class CircleItem(GeoItem):
    """Circle defined by center PointItem and a radius PointItem (or fixed radius)."""

    def __init__(self, center: PointItem, radius_point: PointItem,
                 color=None, width=None):
        super().__init__(color, width)
        self.center_pt = center
        self.radius_pt = radius_point
        center.add_dependent(self)
        radius_point.add_dependent(self)
        self.setZValue(1)

    def remove_from_scene(self):
        self.center_pt.remove_dependent(self)
        self.radius_pt.remove_dependent(self)

    def _radius(self) -> float:
        sc = self.center_pt.scenePos()
        sr = self.radius_pt.scenePos()
        dx = sr.x() - sc.x()
        dy = sr.y() - sc.y()
        return math.sqrt(dx * dx + dy * dy)

    def _local_center(self) -> QPointF:
        return self.mapFromScene(self.center_pt.scenePos())

    def boundingRect(self) -> QRectF:
        lc = self._local_center()
        r = self._radius() + self.stroke_width + 4
        return QRectF(lc.x() - r, lc.y() - r, r * 2, r * 2)

    def shape(self):
        path = QPainterPath()
        path.addEllipse(self._local_center(), self._radius(), self._radius())
        return stroke_shape(path)

    def paint(self, painter: QPainter, option, widget=None):
        lc = self._local_center()
        r = self._radius()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        painter.setPen(pen)
        painter.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawEllipse(lc, r, r)
