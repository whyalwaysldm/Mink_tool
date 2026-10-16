import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QColor, QFont, QFontMetrics
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem
from .segment import SegmentItem


class SegmentMeasureItem(GeoItem):
    """
    Nhãn động hiển thị độ dài đoạn thẳng.
    Tự cập nhật khi điểm đầu / cuối di chuyển.
    """

    def __init__(self, seg: SegmentItem, color=None):
        super().__init__(color)
        self.seg = seg
        seg.p1.add_dependent(self)
        seg.p2.add_dependent(self)
        self.setZValue(4)
        self._font = QFont("Arial", 9)
        self._font.setBold(True)

    def remove_from_scene(self):
        self.seg.p1.remove_dependent(self)
        self.seg.p2.remove_dependent(self)

    # ── Geometry helpers ──────────────────────────────────────────────────

    def _seg_len_px(self) -> float:
        sp1 = self.seg.p1.scenePos()
        sp2 = self.seg.p2.scenePos()
        dx = sp2.x() - sp1.x()
        dy = sp2.y() - sp1.y()
        return math.sqrt(dx * dx + dy * dy)

    def _label(self) -> str:
        return f"ℓ = {self._seg_len_px():.1f}"

    def _auto_center(self) -> QPointF:
        """Tâm nhãn = trung điểm đoạn + 22 px theo pháp tuyến."""
        sp1 = self.seg.p1.scenePos()
        sp2 = self.seg.p2.scenePos()
        mx = (sp1.x() + sp2.x()) / 2
        my = (sp1.y() + sp2.y()) / 2
        dx = sp2.x() - sp1.x()
        dy = sp2.y() - sp1.y()
        length = math.sqrt(dx * dx + dy * dy) or 1
        # Pháp tuyến hướng "bên phải" (theo chiều đoạn)
        nx, ny = -dy / length, dx / length
        return QPointF(mx + nx * 22, my + ny * 22)

    def _text_rect(self) -> QRectF:
        c = self._auto_center()
        fm = QFontMetrics(self._font)
        text = self._label()
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        pad = 4
        return QRectF(c.x() - tw / 2 - pad,
                      c.y() - th / 2 - pad,
                      tw + pad * 2,
                      th + pad * 2)

    # ── QGraphicsItem interface ────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return self._text_rect().adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option, widget=None):
        text = self._label()
        rect = self._text_rect()
        selected = self.isSelected()
        fg = QColor(0, 120, 215) if selected else self.color
        bg = QColor(255, 255, 240, 220)   # vàng nhạt

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font)

        # Nền
        painter.fillRect(rect, bg)

        # Viền
        pen = QPen(fg, 1)
        painter.setPen(pen)
        painter.drawRect(rect)

        # Chữ
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)


class AngleMeasureItem(GeoItem):
    """
    Nhãn động hiển thị góc tại đỉnh (vertex) giữa hai tia p1–vertex và p2–vertex.
    Click thứ tự: cạnh 1 (p1) → đỉnh (vertex) → cạnh 2 (p2).
    """

    def __init__(self, vertex: PointItem, p1: PointItem, p2: PointItem,
                 color=None):
        super().__init__(color)
        self.vertex = vertex
        self.p1 = p1
        self.p2 = p2
        for p in (vertex, p1, p2):
            p.add_dependent(self)
        self.setZValue(4)
        self._font = QFont("Arial", 9)
        self._font.setBold(True)

    def remove_from_scene(self):
        for p in (self.vertex, self.p1, self.p2):
            p.remove_dependent(self)

    # ── Geometry helpers ──────────────────────────────────────────────────

    def _angle_deg(self) -> float:
        sv  = self.vertex.scenePos()
        sp1 = self.p1.scenePos()
        sp2 = self.p2.scenePos()
        v1x, v1y = sp1.x() - sv.x(), sp1.y() - sv.y()
        v2x, v2y = sp2.x() - sv.x(), sp2.y() - sv.y()
        dot = v1x * v2x + v1y * v2y
        l1  = math.sqrt(v1x * v1x + v1y * v1y)
        l2  = math.sqrt(v2x * v2x + v2y * v2y)
        if l1 < 1e-6 or l2 < 1e-6:
            return 0.0
        cos_a = max(-1.0, min(1.0, dot / (l1 * l2)))
        return math.degrees(math.acos(cos_a))

    def _label(self) -> str:
        return f"∠ = {self._angle_deg():.1f}°"

    def _auto_center(self) -> QPointF:
        """Dọc theo đường phân giác, cách đỉnh 42 px."""
        sv  = self.vertex.scenePos()
        sp1 = self.p1.scenePos()
        sp2 = self.p2.scenePos()
        v1x, v1y = sp1.x() - sv.x(), sp1.y() - sv.y()
        v2x, v2y = sp2.x() - sv.x(), sp2.y() - sv.y()
        l1 = math.sqrt(v1x * v1x + v1y * v1y) or 1
        l2 = math.sqrt(v2x * v2x + v2y * v2y) or 1
        bx = v1x / l1 + v2x / l2
        by = v1y / l1 + v2y / l2
        lb = math.sqrt(bx * bx + by * by) or 1
        DIST = 42
        return QPointF(sv.x() + bx / lb * DIST, sv.y() + by / lb * DIST)

    def _text_rect(self) -> QRectF:
        c = self._auto_center()
        fm = QFontMetrics(self._font)
        text = self._label()
        tw = fm.horizontalAdvance(text)
        th = fm.height()
        pad = 4
        return QRectF(c.x() - tw / 2 - pad,
                      c.y() - th / 2 - pad,
                      tw + pad * 2,
                      th + pad * 2)

    # ── QGraphicsItem interface ────────────────────────────────────────────

    def boundingRect(self) -> QRectF:
        return self._text_rect().adjusted(-2, -2, 2, 2)

    def paint(self, painter: QPainter, option, widget=None):
        text = self._label()
        rect = self._text_rect()
        selected = self.isSelected()
        fg = QColor(0, 120, 215) if selected else self.color
        bg = QColor(240, 255, 240, 220)   # xanh lá nhạt

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setFont(self._font)

        painter.fillRect(rect, bg)

        pen = QPen(fg, 1)
        painter.setPen(pen)
        painter.drawRect(rect)

        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
