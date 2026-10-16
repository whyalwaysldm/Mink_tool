from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem


class PolygonItem(GeoItem):
    """Closed polygon defined by a list of PointItems."""

    def __init__(self, points: list, color=None, width=None,
                 fill_color=None, closed=True):
        super().__init__(color, width)
        self.points: list = list(points)
        self.fill_color: QColor = fill_color or QColor(200, 220, 255, 60)
        self.closed = closed
        for p in self.points:
            p.add_dependent(self)
        self.setZValue(1)

    def remove_from_scene(self):
        for p in self.points:
            p.remove_dependent(self)

    def _local_poly(self) -> list:
        return [self.mapFromScene(p.scenePos()) for p in self.points]

    def boundingRect(self) -> QRectF:
        pts = self._local_poly()
        if not pts:
            return QRectF()
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        pad = self.stroke_width + 4
        return QRectF(min(xs) - pad, min(ys) - pad,
                      max(xs) - min(xs) + pad * 2,
                      max(ys) - min(ys) + pad * 2)

    def paint(self, painter: QPainter, option, widget=None):
        pts = self._local_poly()
        if len(pts) < 2:
            return
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.fill_color) if self.closed else
                         QBrush(Qt.BrushStyle.NoBrush))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        poly = QPolygonF(pts)
        if self.closed:
            painter.drawPolygon(poly)
        else:
            painter.drawPolyline(poly)


class TriangleItem(PolygonItem):
    """Convenience subclass locked to 3 vertices."""

    def __init__(self, p1: PointItem, p2: PointItem, p3: PointItem,
                 color=None, width=None, fill_color=None):
        super().__init__([p1, p2, p3], color, width, fill_color, closed=True)
