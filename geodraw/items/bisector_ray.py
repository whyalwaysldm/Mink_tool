import math
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem, stroke_shape
from .point import PointItem

EXTEND = 5000.0


class BisectorRayItem(GeoItem):
    """Ray from vertex along the angle bisector of angle p1-vertex-p2."""

    def __init__(self, p_ray1: PointItem, vertex: PointItem, p_ray2: PointItem,
                 color=None, width=None):
        super().__init__(color, width)
        self._p1 = p_ray1
        self._vertex = vertex
        self._p2 = p_ray2
        p_ray1.add_dependent(self)
        vertex.add_dependent(self)
        p_ray2.add_dependent(self)
        self.setZValue(0)

    def remove_from_scene(self):
        self._p1.remove_dependent(self)
        self._vertex.remove_dependent(self)
        self._p2.remove_dependent(self)

    def _bisector_dir(self) -> QPointF:
        v = self._vertex.scenePos()
        a = self._p1.scenePos()
        b = self._p2.scenePos()
        da_x = a.x() - v.x()
        da_y = a.y() - v.y()
        db_x = b.x() - v.x()
        db_y = b.y() - v.y()
        la = math.sqrt(da_x**2 + da_y**2) or 1e-9
        lb = math.sqrt(db_x**2 + db_y**2) or 1e-9
        ux, uy = da_x / la, da_y / la
        vx, vy = db_x / lb, db_y / lb
        bx, by = ux + vx, uy + vy
        bl = math.sqrt(bx**2 + by**2)
        if bl < 0.001:
            bx, by = -uy, ux
            bl = 1.0
        return QPointF(bx / bl, by / bl)

    def _endpoints(self):
        v = self._vertex.scenePos()
        d = self._bisector_dir()
        end = QPointF(v.x() + d.x() * EXTEND, v.y() + d.y() * EXTEND)
        return self.mapFromScene(v), self.mapFromScene(end)

    def boundingRect(self) -> QRectF:
        a, b = self._endpoints()
        pad = self.stroke_width + 4
        return QRectF(
            min(a.x(), b.x()) - pad, min(a.y(), b.y()) - pad,
            max(abs(a.x() - b.x()) + pad * 2, 1),
            max(abs(a.y() - b.y()) + pad * 2, 1),
        )

    def shape(self):
        a, b = self._endpoints()
        path = QPainterPath(a)
        path.lineTo(b)
        return stroke_shape(path)

    def paint(self, painter: QPainter, option, widget=None):
        a, b = self._endpoints()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawLine(a, b)
