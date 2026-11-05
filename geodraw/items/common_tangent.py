"""
Tiếp tuyến chung của 2 đường tròn.

Có tối đa 4 tiếp tuyến chung: 2 tiếp tuyến chung ngoài (s = +1) và 2 tiếp
tuyến chung trong (s = −1), mỗi loại 2 phía (side = ±1). Tùy vị trí 2 đường
tròn mà một số tiếp tuyến không tồn tại → tiếp điểm và tiếp tuyến tự ẩn,
khi 2 đường tròn di chuyển trở lại thì tự hiện ra.

• CommonTangentPointItem — tiếp điểm trên đường tròn 1 hoặc 2.
• CommonTangentLineItem  — tiếp tuyến: đoạn qua 2 tiếp điểm, kéo dài thêm
  một chút ở 2 đầu.
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainterPath
from PyQt6.QtCore import QPointF, QRectF
from .point import PointItem
from .segment import SegmentItem
from .base import stroke_shape

EXTEND_RATIO = 0.25     # kéo dài tiếp tuyến thêm 25% độ dài mỗi đầu
EXTEND_MIN = 20.0       # … nhưng ít nhất 20 px


def common_tangent(c1: tuple, c2: tuple, s: int, side: int):
    """(T1, T2) tiếp điểm trên 2 đường tròn, hoặc None nếu không tồn tại.
    s = +1: tiếp tuyến chung ngoài, −1: tiếp tuyến chung trong."""
    (o1, r1), (o2, r2) = (c1[1], c1[2]), (c2[1], c2[2])
    dx, dy = o2.x() - o1.x(), o2.y() - o1.y()
    d = math.hypot(dx, dy)
    if d < 1e-9:
        return None
    k = (s * r2 - r1) / d
    if abs(k) > 1 + 1e-9:
        return None
    h = math.sqrt(max(0.0, 1 - k * k))
    if h < 1e-6 and side < 0:
        return None                   # 2 tiếp tuyến trùng nhau → chỉ giữ 1
    ux, uy = dx / d, dy / d
    nx = k * ux - side * h * uy
    ny = k * uy + side * h * ux
    return (QPointF(o1.x() - r1 * nx, o1.y() - r1 * ny),
            QPointF(o2.x() - s * r2 * nx, o2.y() - s * r2 * ny))


class CommonTangentPointItem(PointItem):
    is_constrained = True

    def __init__(self, circle1, circle2, s: int, side: int, which: int,
                 anchors: list, color=None):
        self._updating = False
        self._circles = (circle1, circle2)
        self._s, self._side, self._which = s, side, which
        self._anchors = list(anchors)
        self.exists = True
        super().__init__(QPointF(0, 0), color)
        for a in self._anchors:
            a.add_dependent(self)
        self.update_position()

    def update_position(self):
        from utils.snap_engine import curves_of
        cs = [curves_of(c) for c in self._circles]
        t = common_tangent(cs[0][0], cs[1][0], self._s, self._side) \
            if all(cs) else None
        self.exists = t is not None
        self.setVisible(self.exists)
        if t is None:
            return
        self._updating = True
        self.setPos(t[self._which])
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for a in self._anchors:
                a.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for a in self._anchors:
            a.remove_dependent(self)


class CommonTangentLineItem(SegmentItem):
    """Tiếp tuyến qua 2 tiếp điểm; ẩn khi tiếp tuyến không tồn tại."""

    def _ends(self):
        a, b = self._lp1(), self._lp2()
        dx, dy = b.x() - a.x(), b.y() - a.y()
        L = math.hypot(dx, dy)
        if L < 1e-6:
            # 2 đường tròn tiếp xúc: 2 tiếp điểm trùng nhau → tiếp tuyến vuông
            # góc với đường nối tâm tại tiếp điểm
            from utils.snap_engine import curves_of
            cs = [curves_of(c) for c in getattr(self.p1, '_circles', ())]
            if len(cs) != 2 or not all(cs):
                return a, b
            o1, o2 = cs[0][0][1], cs[1][0][1]
            ux, uy = o2.x() - o1.x(), o2.y() - o1.y()
            n = math.hypot(ux, uy) or 1.0
            half = max(EXTEND_MIN * 2, 0.6 * min(cs[0][0][2], cs[1][0][2]))
            px, py = -uy / n * half, ux / n * half
            return QPointF(a.x() - px, a.y() - py), QPointF(a.x() + px, a.y() + py)
        e = max(EXTEND_MIN, L * EXTEND_RATIO) / L
        return (QPointF(a.x() - dx * e, a.y() - dy * e),
                QPointF(b.x() + dx * e, b.y() + dy * e))

    def _exists(self) -> bool:
        return getattr(self.p1, 'exists', True) and getattr(self.p2, 'exists', True)

    def boundingRect(self) -> QRectF:
        a, b = self._ends()
        pad = self.stroke_width + 6
        return QRectF(a, b).normalized().adjusted(-pad, -pad, pad, pad)

    def shape(self) -> QPainterPath:
        if not self._exists():
            return QPainterPath()
        a, b = self._ends()
        path = QPainterPath(a)
        path.lineTo(b)
        return stroke_shape(path)

    def paint(self, painter, option, widget=None):
        if not self._exists():
            return
        from PyQt6.QtGui import QPainter, QPen, QColor
        from PyQt6.QtCore import Qt
        a, b = self._ends()
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        pen = QPen(color, self.stroke_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawLine(a, b)
