import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem


class SegmentItem(GeoItem):

    def __init__(self, p1: PointItem, p2: PointItem, color=None, width=None):
        super().__init__(color, width)
        self.p1 = p1
        self.p2 = p2
        p1.add_dependent(self)
        p2.add_dependent(self)
        self.setZValue(1)

    # ── itemChange: dependency + Z khi chọn ────────────────────────────
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            # Khi được chọn: nổi lên trên các đoạn khác để nhìn thấy rõ
            # (Z=3 > mặc định Z=1; vẫn dưới PointItem Z=10)
            self.setZValue(3 if value else 1)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene() is not None:
                self.p1.add_dependent(self)   # idempotent — không thêm trùng
                self.p2.add_dependent(self)
        return super().itemChange(change, value)

    def remove_from_scene(self):
        self.p1.remove_dependent(self)
        self.p2.remove_dependent(self)

    def length(self) -> float:
        sp1, sp2 = self.p1.scenePos(), self.p2.scenePos()
        dx, dy = sp2.x() - sp1.x(), sp2.y() - sp1.y()
        return math.sqrt(dx * dx + dy * dy)

    def _scene_to_local(self, scene_pos: QPointF) -> QPointF:
        return self.mapFromScene(scene_pos)

    def _lp1(self) -> QPointF:
        return self.mapFromScene(self.p1.scenePos())

    def _lp2(self) -> QPointF:
        return self.mapFromScene(self.p2.scenePos())

    def boundingRect(self) -> QRectF:
        lp1 = self._lp1()
        lp2 = self._lp2()
        pad = self.stroke_width + 6
        x = min(lp1.x(), lp2.x()) - pad
        y = min(lp1.y(), lp2.y()) - pad
        w = abs(lp1.x() - lp2.x()) + pad * 2
        h = abs(lp1.y() - lp2.y()) + pad * 2
        return QRectF(x, y, max(w, 1), max(h, 1))

    def shape(self) -> QPainterPath:
        """Vùng click là dải mỏng dọc theo đoạn thẳng (không phải toàn bộ bounding rect)."""
        lp1 = self._lp1()
        lp2 = self._lp2()
        HIT_W = max(self.stroke_width + 8, 10)   # bề rộng vùng nhạy click (px)
        dx = lp2.x() - lp1.x()
        dy = lp2.y() - lp1.y()
        length = math.sqrt(dx * dx + dy * dy)
        if length < 1e-6:
            path = QPainterPath()
            path.addEllipse(lp1, HIT_W, HIT_W)
            return path
        # Vector vuông góc đơn vị
        nx = -dy / length * (HIT_W / 2)
        ny =  dx / length * (HIT_W / 2)
        path = QPainterPath()
        path.moveTo(lp1.x() + nx, lp1.y() + ny)
        path.lineTo(lp2.x() + nx, lp2.y() + ny)
        path.lineTo(lp2.x() - nx, lp2.y() - ny)
        path.lineTo(lp1.x() - nx, lp1.y() - ny)
        path.closeSubpath()
        return path

    def paint(self, painter: QPainter, option, widget=None):
        lp1 = self._lp1()
        lp2 = self._lp2()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawLine(lp1, lp2)
