import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem

EXTEND = 5000.0


class LineItem(GeoItem):
    """Infinite line through p1 and p2, clipped to a large extent."""

    def __init__(self, p1: PointItem, p2: PointItem, color=None, width=None):
        super().__init__(color, width)
        self.p1 = p1
        self.p2 = p2
        p1.add_dependent(self)
        p2.add_dependent(self)
        self.setZValue(0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.setZValue(2 if value else 0)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene() is not None:
                self.p1.add_dependent(self)
                self.p2.add_dependent(self)
        return super().itemChange(change, value)

    def remove_from_scene(self):
        self.p1.remove_dependent(self)
        self.p2.remove_dependent(self)

    def _endpoints(self) -> tuple:
        sp1 = self.p1.scenePos()
        sp2 = self.p2.scenePos()
        dx = sp2.x() - sp1.x()
        dy = sp2.y() - sp1.y()
        length = math.sqrt(dx * dx + dy * dy) or 1
        ux, uy = dx / length, dy / length
        a = self.mapFromScene(QPointF(sp1.x() - ux * EXTEND, sp1.y() - uy * EXTEND))
        b = self.mapFromScene(QPointF(sp1.x() + ux * EXTEND, sp1.y() + uy * EXTEND))
        return a, b

    def boundingRect(self) -> QRectF:
        a, b = self._endpoints()
        pad = self.stroke_width + 4
        x = min(a.x(), b.x()) - pad
        y = min(a.y(), b.y()) - pad
        w = abs(a.x() - b.x()) + pad * 2
        h = abs(a.y() - b.y()) + pad * 2
        return QRectF(x, y, max(w, 1), max(h, 1))

    def paint(self, painter: QPainter, option, widget=None):
        a, b = self._endpoints()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawLine(a, b)


class RayItem(GeoItem):
    """Ray starting at p1, going through p2."""

    def __init__(self, p1: PointItem, p2: PointItem, color=None, width=None):
        super().__init__(color, width)
        self.p1 = p1
        self.p2 = p2
        p1.add_dependent(self)
        p2.add_dependent(self)
        self.setZValue(0)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.setZValue(2 if value else 0)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene() is not None:
                self.p1.add_dependent(self)
                self.p2.add_dependent(self)
        return super().itemChange(change, value)

    def remove_from_scene(self):
        self.p1.remove_dependent(self)
        self.p2.remove_dependent(self)

    def _endpoints(self) -> tuple:
        sp1 = self.p1.scenePos()
        sp2 = self.p2.scenePos()
        dx = sp2.x() - sp1.x()
        dy = sp2.y() - sp1.y()
        length = math.sqrt(dx * dx + dy * dy) or 1
        ux, uy = dx / length, dy / length
        a = self.mapFromScene(sp1)
        b = self.mapFromScene(QPointF(sp1.x() + ux * EXTEND, sp1.y() + uy * EXTEND))
        return a, b

    def boundingRect(self) -> QRectF:
        a, b = self._endpoints()
        pad = self.stroke_width + 4
        x = min(a.x(), b.x()) - pad
        y = min(a.y(), b.y()) - pad
        w = abs(a.x() - b.x()) + pad * 2
        h = abs(a.y() - b.y()) + pad * 2
        return QRectF(x, y, max(w, 1), max(h, 1))

    def paint(self, painter: QPainter, option, widget=None):
        a, b = self._endpoints()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawLine(a, b)
