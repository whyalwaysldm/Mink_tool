import math
from PyQt6.QtGui import QPainter, QPen, QPainterPath, QColor
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem


class ArcItem(GeoItem):
    """Arc through three points: start, through-point, end."""

    def __init__(self, p_start: PointItem, p_mid: PointItem, p_end: PointItem,
                 color=None, width=None):
        super().__init__(color, width)
        self.p_start = p_start
        self.p_mid = p_mid
        self.p_end = p_end
        for p in (p_start, p_mid, p_end):
            p.add_dependent(self)
        self.setZValue(1)

    def remove_from_scene(self):
        for p in (self.p_start, self.p_mid, self.p_end):
            p.remove_dependent(self)

    def _circle_from_3pts(self, a: QPointF, b: QPointF, c: QPointF):
        ax, ay = a.x(), a.y()
        bx, by = b.x(), b.y()
        cx, cy = c.x(), c.y()
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < 1e-9:
            return None, None
        ux = ((ax*ax + ay*ay)*(by - cy) + (bx*bx + by*by)*(cy - ay)
              + (cx*cx + cy*cy)*(ay - by)) / d
        uy = ((ax*ax + ay*ay)*(cx - bx) + (bx*bx + by*by)*(ax - cx)
              + (cx*cx + cy*cy)*(bx - ax)) / d
        r = math.sqrt((ax - ux)**2 + (ay - uy)**2)
        return QPointF(ux, uy), r

    def _build_path(self) -> QPainterPath:
        sa = self.p_start.scenePos()
        sm = self.p_mid.scenePos()
        se = self.p_end.scenePos()
        center, r = self._circle_from_3pts(sa, sm, se)
        path = QPainterPath()
        if center is None:
            lsa = self.mapFromScene(sa)
            lse = self.mapFromScene(se)
            path.moveTo(lsa)
            path.lineTo(lse)
            return path
        lc = self.mapFromScene(center)
        rect = QRectF(lc.x() - r, lc.y() - r, r * 2, r * 2)
        lsa = self.mapFromScene(sa)
        lse = self.mapFromScene(se)
        start_angle = math.degrees(math.atan2(-(lsa.y() - lc.y()), lsa.x() - lc.x()))
        end_angle = math.degrees(math.atan2(-(lse.y() - lc.y()), lse.x() - lc.x()))
        lsm = self.mapFromScene(sm)
        mid_angle = math.degrees(math.atan2(-(lsm.y() - lc.y()), lsm.x() - lc.x()))

        def normalize(a):
            while a < 0: a += 360
            while a >= 360: a -= 360
            return a

        def angle_between(start, mid, end, cw):
            s, m, e = normalize(start), normalize(mid), normalize(end)
            if cw:
                span = (s - e) % 360
                check = (s - m) % 360
            else:
                span = (e - s) % 360
                check = (m - s) % 360
            return check <= span

        cw = not angle_between(start_angle, mid_angle, end_angle, False)
        span = (start_angle - end_angle) % 360 if cw else (end_angle - start_angle) % 360
        if cw:
            span = -span if span > 0 else span

        path.arcMoveTo(rect, start_angle)
        path.arcTo(rect, start_angle, span if not cw else -((360 - span) % 360))
        return path

    def boundingRect(self) -> QRectF:
        return self._build_path().boundingRect().adjusted(-4, -4, 4, 4)

    def paint(self, painter: QPainter, option, widget=None):
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawPath(self._build_path())
