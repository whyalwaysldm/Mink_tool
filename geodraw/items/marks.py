import math
from PyQt6.QtGui import QPainter, QPen, QPainterPath, QColor
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem
from .segment import SegmentItem


class AngleMarkItem(GeoItem):
    """Small arc at a vertex between two segments."""

    def __init__(self, vertex: PointItem, p1: PointItem, p2: PointItem,
                 color=None, radius=18.0, count=1):
        super().__init__(color)
        self.vertex = vertex
        self.p1 = p1
        self.p2 = p2
        self.radius = radius
        self.count = count  # 1 or 2 arcs
        for p in (vertex, p1, p2):
            p.add_dependent(self)
        self.setZValue(2)

    def remove_from_scene(self):
        for p in (self.vertex, self.p1, self.p2):
            p.remove_dependent(self)

    def _angles(self):
        sv = self.vertex.scenePos()
        a1 = math.degrees(math.atan2(-(self.p1.scenePos().y() - sv.y()),
                                      self.p1.scenePos().x() - sv.x()))
        a2 = math.degrees(math.atan2(-(self.p2.scenePos().y() - sv.y()),
                                      self.p2.scenePos().x() - sv.x()))
        span = (a2 - a1) % 360
        if span > 180:
            span -= 360
        return a1, span

    def boundingRect(self) -> QRectF:
        lv = self.mapFromScene(self.vertex.scenePos())
        r = self.radius + 4
        return QRectF(lv.x() - r, lv.y() - r, r * 2, r * 2)

    def paint(self, painter: QPainter, option, widget=None):
        lv = self.mapFromScene(self.vertex.scenePos())
        a1, span = self._angles()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for i in range(self.count):
            r = self.radius - i * 4
            rect = QRectF(lv.x() - r, lv.y() - r, r * 2, r * 2)
            painter.drawArc(rect, int(a1 * 16), int(span * 16))


class RightAngleMarkItem(GeoItem):
    """Small square at a right-angle vertex."""

    def __init__(self, vertex: PointItem, p1: PointItem, p2: PointItem,
                 color=None, size=10.0):
        super().__init__(color)
        self.vertex = vertex
        self.p1 = p1
        self.p2 = p2
        self.size = size
        for p in (vertex, p1, p2):
            p.add_dependent(self)
        self.setZValue(2)

    def remove_from_scene(self):
        for p in (self.vertex, self.p1, self.p2):
            p.remove_dependent(self)

    def _square_pts(self) -> list:
        sv = self.vertex.scenePos()
        sp1 = self.p1.scenePos()
        sp2 = self.p2.scenePos()

        def unit(a, b):
            dx, dy = b.x() - a.x(), b.y() - a.y()
            l = math.sqrt(dx*dx + dy*dy) or 1
            return dx/l, dy/l

        u1x, u1y = unit(sv, sp1)
        u2x, u2y = unit(sv, sp2)
        s = self.size
        pts = [
            self.mapFromScene(sv),
            self.mapFromScene(QPointF(sv.x() + u1x*s, sv.y() + u1y*s)),
            self.mapFromScene(QPointF(sv.x() + u1x*s + u2x*s,
                                      sv.y() + u1y*s + u2y*s)),
            self.mapFromScene(QPointF(sv.x() + u2x*s, sv.y() + u2y*s)),
        ]
        return pts

    def boundingRect(self) -> QRectF:
        pts = self._square_pts()
        xs = [p.x() for p in pts]
        ys = [p.y() for p in pts]
        return QRectF(min(xs)-2, min(ys)-2,
                      max(xs)-min(xs)+4, max(ys)-min(ys)+4)

    def paint(self, painter: QPainter, option, widget=None):
        pts = self._square_pts()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.moveTo(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        path.closeSubpath()
        painter.drawPath(path)


class EqualMarkItem(GeoItem):
    """Tick marks on a segment indicating equal lengths."""

    def __init__(self, seg: SegmentItem, color=None, count=1):
        super().__init__(color)
        self.seg = seg
        self.count = count
        seg.p1.add_dependent(self)
        seg.p2.add_dependent(self)
        self.setZValue(2)

    def remove_from_scene(self):
        self.seg.p1.remove_dependent(self)
        self.seg.p2.remove_dependent(self)

    # ── Kích thước tỷ lệ theo stroke_width của preset ─────────────────
    def _tick_size(self) -> float:
        """Độ dài nửa gạch (px), tỷ lệ với stroke_width."""
        return max(3.5, self.stroke_width * 2.3)

    def _tick_spacing(self) -> float:
        """Khoảng cách giữa các gạch (px)."""
        return max(2.8, self.stroke_width * 1.9)

    def _tick_pts(self) -> list:
        sp1 = self.seg.p1.scenePos()
        sp2 = self.seg.p2.scenePos()
        mx = (sp1.x() + sp2.x()) / 2
        my = (sp1.y() + sp2.y()) / 2
        dx = sp2.x() - sp1.x()
        dy = sp2.y() - sp1.y()
        length = math.sqrt(dx*dx + dy*dy) or 1
        ux, uy = dx/length, dy/length   # dọc đoạn
        nx, ny = -uy, ux                # vuông góc

        size    = self._tick_size()
        spacing = self._tick_spacing()

        if self.count == 4:             # ── Dấu × ──
            s = size
            a = self.mapFromScene(QPointF(mx - ux*s - nx*s, my - uy*s - ny*s))
            b = self.mapFromScene(QPointF(mx + ux*s + nx*s, my + uy*s + ny*s))
            c = self.mapFromScene(QPointF(mx + ux*s - nx*s, my + uy*s - ny*s))
            d = self.mapFromScene(QPointF(mx - ux*s + nx*s, my - uy*s + ny*s))
            return [(a, b), (c, d)]

        # ── Gạch đứng (1 / 2 / 3) ──
        offsets = {1: [0.0],
                   2: [-spacing/2, spacing/2],
                   3: [-spacing,   0.0,       spacing]}.get(self.count, [0.0])
        result = []
        for off in offsets:
            cx = mx + ux * off
            cy = my + uy * off
            a = self.mapFromScene(QPointF(cx - nx*size, cy - ny*size))
            b = self.mapFromScene(QPointF(cx + nx*size, cy + ny*size))
            result.append((a, b))
        return result

    def boundingRect(self) -> QRectF:
        ticks = self._tick_pts()
        if not ticks:
            return QRectF()
        xs = [p.x() for pair in ticks for p in pair]
        ys = [p.y() for pair in ticks for p in pair]
        return QRectF(min(xs)-2, min(ys)-2,
                      max(xs)-min(xs)+4, max(ys)-min(ys)+4)

    def paint(self, painter: QPainter, option, widget=None):
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for a, b in self._tick_pts():
            painter.drawLine(a, b)


class ParallelMarkItem(GeoItem):
    """Arrow ticks on a segment indicating parallel lines."""

    def __init__(self, seg: SegmentItem, color=None, count=1):
        super().__init__(color)
        self.seg = seg
        self.count = count
        seg.p1.add_dependent(self)
        seg.p2.add_dependent(self)
        self.setZValue(2)

    def remove_from_scene(self):
        self.seg.p1.remove_dependent(self)
        self.seg.p2.remove_dependent(self)

    # ── Kích thước tỷ lệ theo stroke_width ────────────────────────────
    def _arrow_size(self) -> float:
        return max(4.0, self.stroke_width * 2.8)

    def _arrow_pts(self) -> list:
        sp1 = self.seg.p1.scenePos()
        sp2 = self.seg.p2.scenePos()
        mx = (sp1.x() + sp2.x()) / 2
        my = (sp1.y() + sp2.y()) / 2
        dx = sp2.x() - sp1.x()
        dy = sp2.y() - sp1.y()
        length = math.sqrt(dx*dx + dy*dy) or 1
        ux, uy = dx/length, dy/length
        nx, ny = -uy, ux
        size    = self._arrow_size()
        spacing = size
        offsets = [0.0] if self.count == 1 else [-spacing/2, spacing/2]
        result = []
        for off in offsets:
            cx = mx + ux * off
            cy = my + uy * off
            tip = self.mapFromScene(QPointF(cx + ux*size, cy + uy*size))
            bl  = self.mapFromScene(QPointF(cx - ux*size + nx*size*0.6,
                                            cy - uy*size + ny*size*0.6))
            br  = self.mapFromScene(QPointF(cx - ux*size - nx*size*0.6,
                                            cy - uy*size - ny*size*0.6))
            result.append((tip, bl, br))
        return result

    def boundingRect(self) -> QRectF:
        pts_flat = [p for tri in self._arrow_pts() for p in tri]
        if not pts_flat:
            return QRectF()
        xs = [p.x() for p in pts_flat]
        ys = [p.y() for p in pts_flat]
        return QRectF(min(xs)-2, min(ys)-2,
                      max(xs)-min(xs)+4, max(ys)-min(ys)+4)

    def paint(self, painter: QPainter, option, widget=None):
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for tip, bl, br in self._arrow_pts():
            path = QPainterPath()
            path.moveTo(bl)
            path.lineTo(tip)
            path.lineTo(br)
            painter.drawPath(path)
