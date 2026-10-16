import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPainterPath, QBrush, QColor, QPen
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from utils.geometry import perpendicular_offset

_TWO_PI = 2 * math.pi

MIN_DIST = 2.0
BASE_WIDTH = 3.0


class InkStrokeItem(GeoItem):

    def __init__(self, color=None, base_width=BASE_WIDTH):
        super().__init__(color)
        self.base_width = base_width
        self._samples: list = []        # [(QPointF, pressure)]
        self._live_path = QPainterPath()  # polyline nhanh khi đang vẽ
        self._final_path = QPainterPath() # outline đầy đủ sau khi nhả
        self._finalized = False
        self._bounding = QRectF()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(3)

    def add_sample(self, pos: QPointF, pressure: float):
        if self._samples:
            last = self._samples[-1][0]
            dx = pos.x() - last.x()
            dy = pos.y() - last.y()
            if math.sqrt(dx * dx + dy * dy) < MIN_DIST:
                return
        self._samples.append((pos, pressure))
        self._update_live(pos)

    def _update_live(self, pos: QPointF):
        """Chỉ thêm điểm mới vào polyline — O(1), không tính lại toàn bộ."""
        if len(self._samples) == 1:
            self._live_path = QPainterPath()
            self._live_path.moveTo(pos)
            self._bounding = QRectF(pos.x() - 1, pos.y() - 1, 2, 2)
        else:
            self._live_path.lineTo(pos)
            # mở rộng bounding box tăng dần
            b = self._bounding
            self._bounding = QRectF(
                min(b.left(),   pos.x() - self.base_width),
                min(b.top(),    pos.y() - self.base_width),
                max(b.right(),  pos.x() + self.base_width) - min(b.left(), pos.x() - self.base_width),
                max(b.bottom(), pos.y() + self.base_width) - min(b.top(),  pos.y() - self.base_width),
            )
        self.prepareGeometryChange()
        self.update()

    def finalize(self):
        """Khi nhả bút: tính outline có áp lực — chạy một lần duy nhất."""
        self._final_path = self._build_outline()
        self._finalized = True
        if not self._final_path.isEmpty():
            self._bounding = self._final_path.boundingRect().adjusted(-2, -2, 2, 2)
        self.prepareGeometryChange()
        self.update()

    def _build_outline(self) -> QPainterPath:
        samples = self._samples
        n = len(samples)
        if n < 2:
            return QPainterPath()

        left_pts, right_pts = [], []
        for i in range(n):
            pos, pressure = samples[i]
            w = max(0.5, self.base_width * (pressure ** 0.6))
            if i == 0:
                dx = samples[1][0].x() - pos.x()
                dy = samples[1][0].y() - pos.y()
            elif i == n - 1:
                dx = pos.x() - samples[i-1][0].x()
                dy = pos.y() - samples[i-1][0].y()
            else:
                dx = samples[i+1][0].x() - samples[i-1][0].x()
                dy = samples[i+1][0].y() - samples[i-1][0].y()
            lp, rp = perpendicular_offset(pos, w / 2, QPointF(dx, dy))
            left_pts.append(lp)
            right_pts.append(rp)

        path = QPainterPath()
        # WindingFill: vùng nào có winding-number ≠ 0 đều được tô
        # → tránh "lỗ trắng" khi nét bút tự giao nhau hoặc đè lên nhau
        path.setFillRule(Qt.FillRule.WindingFill)

        # ── Cạnh trái (đi xuôi) ───────────────────────────────────────────
        path.moveTo(left_pts[0])
        for p in left_pts[1:]:
            path.lineTo(p)

        # ── Mũ tròn cuối nét (8 đoạn xấp xỉ bán nguyệt) ─────────────────
        pN, wN = samples[-1]
        rN = max(0.5, self.base_width * (wN ** 0.6)) / 2
        dxN = pN.x() - samples[-2][0].x()
        dyN = pN.y() - samples[-2][0].y()
        base_ang = math.atan2(dyN, dxN)
        STEPS = 8
        for k in range(STEPS + 1):
            a = base_ang - math.pi / 2 + math.pi * k / STEPS
            path.lineTo(QPointF(pN.x() + rN * math.cos(a),
                                pN.y() + rN * math.sin(a)))

        # ── Cạnh phải (đi ngược) ─────────────────────────────────────────
        for p in reversed(right_pts):
            path.lineTo(p)

        # ── Mũ tròn đầu nét ───────────────────────────────────────────────
        p0, w0 = samples[0]
        r0 = max(0.5, self.base_width * (w0 ** 0.6)) / 2
        dx0 = samples[1][0].x() - p0.x()
        dy0 = samples[1][0].y() - p0.y()
        base_ang0 = math.atan2(dy0, dx0) + math.pi   # hướng lui
        for k in range(STEPS + 1):
            a = base_ang0 - math.pi / 2 + math.pi * k / STEPS
            path.lineTo(QPointF(p0.x() + r0 * math.cos(a),
                                p0.y() + r0 * math.sin(a)))

        path.closeSubpath()
        return path

    def boundingRect(self) -> QRectF:
        if self._bounding.isNull():
            return QRectF(-1, -1, 2, 2)
        return self._bounding

    def paint(self, painter: QPainter, option, widget=None):
        color = QColor(0, 120, 215) if self.isSelected() else self.color
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._finalized and not self._final_path.isEmpty():
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(color))
            painter.drawPath(self._final_path)
        elif not self._live_path.isEmpty():
            # vẽ nhanh bằng pen có độ dày khi đang live
            pen = QPen(color, self.base_width)
            pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(self._live_path)
