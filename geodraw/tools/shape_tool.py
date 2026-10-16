import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsPolygonItem
from PyQt6.QtGui import QPen, QBrush, QColor, QPolygonF
from .base_tool import BaseTool
from items.fixed_polygon import FixedPolygonItem


def _dist(a: QPointF, b: QPointF) -> float:
    return math.sqrt((a.x()-b.x())**2 + (a.y()-b.y())**2)


# ── Base class ──────────────────────────────────────────────────────────────

class PresetShapeTool(BaseTool):
    """Click + drag để đặt hình preset. Override compute_vertices()."""
    shape_label: str = "Hình"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._anchor: QPointF = None
        self._pressing = False
        self._ghost: QGraphicsPolygonItem = None

    def activate(self):
        self._anchor = None
        self._pressing = False
        self._remove_ghost()

    def deactivate(self):
        self._anchor = None
        self._pressing = False
        self._remove_ghost()

    def compute_vertices(self, anchor: QPointF, current: QPointF) -> list:
        raise NotImplementedError

    def _remove_ghost(self):
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._ghost = None

    def _ensure_ghost(self):
        if self._ghost is None:
            self._ghost = QGraphicsPolygonItem()
            self._ghost.setPen(QPen(QColor(0, 120, 215, 160), 1.5,
                                    Qt.PenStyle.DashLine))
            self._ghost.setBrush(QBrush(QColor(0, 120, 215, 25)))
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)

    def _update_ghost(self, pts: list):
        self._ensure_ghost()
        self._ghost.setPolygon(QPolygonF(pts))

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate(); self.activate(); return
        self._anchor = pos
        self._pressing = True

    def move(self, pos: QPointF, modifiers):
        if self._pressing and self._anchor:
            if _dist(self._anchor, pos) > 3:
                pts = self.compute_vertices(self._anchor, pos)
                if pts:
                    self._update_ghost(pts)

    def release(self, pos: QPointF, button):
        if not self._pressing or not self._anchor:
            return
        if _dist(self._anchor, pos) > 5:
            pts = self.compute_vertices(self._anchor, pos)
            if pts and len(pts) >= 3:
                item = FixedPolygonItem(pts)
                self.scene.addItem(item)
                self.history.push_add(self.scene, item)
        self._pressing = False
        self._anchor = None
        self._remove_ghost()

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)


# ── Các hình cụ thể ─────────────────────────────────────────────────────────

class RectangleTool(PresetShapeTool):
    name = "rectangle"
    shape_label = "Hình chữ nhật"

    def compute_vertices(self, anchor, current):
        x0, y0 = anchor.x(), anchor.y()
        x1, y1 = current.x(), current.y()
        return [QPointF(x0, y0), QPointF(x1, y0),
                QPointF(x1, y1), QPointF(x0, y1)]


class SquareTool(PresetShapeTool):
    name = "square"
    shape_label = "Hình vuông"

    def compute_vertices(self, anchor, current):
        dx = current.x() - anchor.x()
        dy = current.y() - anchor.y()
        p0 = anchor
        p1 = current
        p2 = QPointF(current.x() - dy, current.y() + dx)
        p3 = QPointF(anchor.x() - dy, anchor.y() + dx)
        return [p0, p1, p2, p3]


class EquilateralTriangleTool(PresetShapeTool):
    name = "equilateral_triangle"
    shape_label = "Tam giác đều"

    def compute_vertices(self, anchor, current):
        r = _dist(anchor, current)
        if r < 1:
            return []
        angle = math.atan2(current.y() - anchor.y(), current.x() - anchor.x())
        return [
            QPointF(anchor.x() + r * math.cos(angle + i * 2 * math.pi / 3),
                    anchor.y() + r * math.sin(angle + i * 2 * math.pi / 3))
            for i in range(3)
        ]


class RightTriangleTool(PresetShapeTool):
    name = "right_triangle"
    shape_label = "Tam giác vuông"

    def compute_vertices(self, anchor, current):
        # góc vuông tại anchor, 2 cạnh góc vuông theo trục
        return [anchor,
                QPointF(current.x(), anchor.y()),
                QPointF(anchor.x(), current.y())]


class IsoscelesRightTriangleTool(PresetShapeTool):
    name = "isosceles_right_triangle"
    shape_label = "Tam giác vuông cân"

    def compute_vertices(self, anchor, current):
        # góc vuông tại anchor, 2 cạnh bằng nhau, hướng theo drag ±45°
        dx = current.x() - anchor.x()
        dy = current.y() - anchor.y()
        leg = math.sqrt(dx*dx + dy*dy)
        if leg < 1:
            return []
        base_angle = math.atan2(dy, dx)
        p1 = QPointF(anchor.x() + leg * math.cos(base_angle + math.pi/4),
                     anchor.y() + leg * math.sin(base_angle + math.pi/4))
        p2 = QPointF(anchor.x() + leg * math.cos(base_angle - math.pi/4),
                     anchor.y() + leg * math.sin(base_angle - math.pi/4))
        return [anchor, p1, p2]


class RhombusTool(PresetShapeTool):
    name = "rhombus"
    shape_label = "Hình thoi"

    def compute_vertices(self, anchor, current):
        # anchor = tâm, drag đến đỉnh
        dx = current.x() - anchor.x()
        dy = current.y() - anchor.y()
        # đường chéo 2 vuông góc, dài bằng 0.65 đường chéo 1
        r = 0.65
        p_right  = current
        p_left   = QPointF(anchor.x() - dx, anchor.y() - dy)
        p_top    = QPointF(anchor.x() - dy * r, anchor.y() + dx * r)
        p_bottom = QPointF(anchor.x() + dy * r, anchor.y() - dx * r)
        return [p_right, p_top, p_left, p_bottom]


class ParallelogramTool(PresetShapeTool):
    name = "parallelogram"
    shape_label = "Hình bình hành"

    def compute_vertices(self, anchor, current):
        dx = current.x() - anchor.x()
        dy = current.y() - anchor.y()
        # cạnh đáy = anchor→current, chiều cao = 0.55 * cạnh đáy
        h = 0.55
        ox = -dy * h
        oy =  dx * h
        p0 = anchor
        p1 = current
        p2 = QPointF(current.x() + ox, current.y() + oy)
        p3 = QPointF(anchor.x() + ox, anchor.y() + oy)
        return [p0, p1, p2, p3]


class IsoscelesTriangleTool(PresetShapeTool):
    name = "isosceles_triangle"
    shape_label = "Tam giác cân"

    def compute_vertices(self, anchor, current):
        # anchor = đỉnh, current = trung điểm đáy
        dx = current.x() - anchor.x()
        dy = current.y() - anchor.y()
        base_half = math.sqrt(dx*dx + dy*dy) * 0.5
        # đáy vuông góc với đường cao
        nx = -dy / (math.sqrt(dx*dx+dy*dy) or 1)
        ny =  dx / (math.sqrt(dx*dx+dy*dy) or 1)
        base_cx, base_cy = current.x(), current.y()
        p1 = QPointF(base_cx + nx * base_half, base_cy + ny * base_half)
        p2 = QPointF(base_cx - nx * base_half, base_cy - ny * base_half)
        return [anchor, p1, p2]


class TrapezoidTool(PresetShapeTool):
    name = "trapezoid"
    shape_label = "Hình thang"

    def compute_vertices(self, anchor, current):
        # đáy lớn = anchor → current (theo trục x)
        x0, y0 = anchor.x(), anchor.y()
        x1, y1 = current.x(), current.y()
        width = x1 - x0
        height = abs(y1 - y0) if abs(y1 - y0) > 5 else abs(width) * 0.6
        h = -height if y1 < y0 else height
        # đáy nhỏ = 55% đáy lớn, căn giữa
        small = width * 0.55
        offset = (width - small) / 2
        p0 = QPointF(x0, y0)
        p1 = QPointF(x1, y0)
        p2 = QPointF(x0 + offset + small, y0 + h)
        p3 = QPointF(x0 + offset,         y0 + h)
        return [p0, p1, p2, p3]


class RegularHexagonTool(PresetShapeTool):
    name = "hexagon"
    shape_label = "Lục giác đều"

    def compute_vertices(self, anchor, current):
        r = _dist(anchor, current)
        if r < 1:
            return []
        angle = math.atan2(current.y() - anchor.y(), current.x() - anchor.x())
        return [
            QPointF(anchor.x() + r * math.cos(angle + i * math.pi / 3),
                    anchor.y() + r * math.sin(angle + i * math.pi / 3))
            for i in range(6)
        ]


class RegularPentagonTool(PresetShapeTool):
    name = "pentagon"
    shape_label = "Ngũ giác đều"

    def compute_vertices(self, anchor, current):
        r = _dist(anchor, current)
        if r < 1:
            return []
        angle = math.atan2(current.y() - anchor.y(), current.x() - anchor.x())
        return [
            QPointF(anchor.x() + r * math.cos(angle + i * 2 * math.pi / 5),
                    anchor.y() + r * math.sin(angle + i * 2 * math.pi / 5))
            for i in range(5)
        ]


# Danh sách tất cả shape tools để đăng ký
ALL_SHAPE_TOOLS = [
    RectangleTool,
    SquareTool,
    EquilateralTriangleTool,
    RightTriangleTool,
    IsoscelesRightTriangleTool,
    IsoscelesTriangleTool,
    RhombusTool,
    ParallelogramTool,
    TrapezoidTool,
    RegularHexagonTool,
    RegularPentagonTool,
]
