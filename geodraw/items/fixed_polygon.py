import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QPolygonF
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem


class FixedPolygonItem(GeoItem):
    """Hình đa giác cố định — vertices lưu trực tiếp, di chuyển cả khối."""

    def __init__(self, points: list, color=None, width=None, fill_color=None):
        super().__init__(color, width)
        self._points: list = [QPointF(p) for p in points]
        self.fill_color: QColor = fill_color or QColor(200, 220, 255, 50)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(1)

    def _poly(self) -> QPolygonF:
        return QPolygonF(self._points)

    def boundingRect(self) -> QRectF:
        if not self._points:
            return QRectF()
        xs = [p.x() for p in self._points]
        ys = [p.y() for p in self._points]
        pad = self.stroke_width + 4
        return QRectF(min(xs) - pad, min(ys) - pad,
                      max(xs) - min(xs) + pad * 2,
                      max(ys) - min(ys) + pad * 2)

    def paint(self, painter: QPainter, option, widget=None):
        if len(self._points) < 2:
            return
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(QBrush(self.fill_color))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPolygon(self._poly())
