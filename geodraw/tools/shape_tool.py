import math
from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsPolygonItem
from PyQt6.QtGui import QPen, QBrush, QColor, QPolygonF
from .base_tool import BaseTool
from items.point import PointItem
from items.shape import ShapeItem
from items.segment import SegmentItem


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
                # Dựng hình từ các điểm đỉnh — kéo đỉnh để đổi cỡ / xoay
                vertices = [PointItem(p) for p in pts]
                n = len(vertices)
                edges = [SegmentItem(vertices[k], vertices[(k + 1) % n])
                         for k in range(n)]
                item = ShapeItem(vertices, self.shape_label,
                                 kind=self.name,
                                 edges=edges)
                self.history.push_add_batch(
                    self.scene, vertices + [item] + edges)
                self.tm.status_hint.emit(
                    f"✓ {self.shape_label} — công cụ Chọn: click cạnh để chọn cạnh, "
                    "double-click để chọn cả hình; kéo đỉnh để đổi cỡ / xoay")
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
        # cạnh đáy = anchor→current, chiều cao = 0.55 * cạnh đáy,
        # cạnh bên nghiêng thêm 0.35 * cạnh đáy (nếu không sẽ thành hình chữ nhật)
        h = 0.55
        s = 0.35
        ox = -dy * h + dx * s
        oy =  dx * h + dy * s
        p0 = anchor
        p1 = current
        p2 = QPointF(current.x() + ox, current.y() + oy)
        p3 = QPointF(anchor.x() + ox, anchor.y() + oy)
        return [p0, p1, p2, p3]


class IsoscelesTriangleTool(PresetShapeTool):
    """
    Tam giác cân vẽ bằng 3 click:
      1. đỉnh (đỉnh cân)   2. đỉnh đáy thứ nhất
      3. đỉnh đáy thứ hai — tự đặt sao cho 2 cạnh bên bằng nhau,
         hướng theo con trỏ (góc ở đỉnh lớn / nhỏ tùy chỗ click).
    """
    name = "isosceles_triangle"
    shape_label = "Tam giác cân"

    def activate(self):
        super().activate()
        self._clicks: list = []
        self.tm.status_hint.emit("Tam giác cân: click đỉnh (đỉnh cân)")

    def deactivate(self):
        super().deactivate()
        self._clicks = []

    def _third(self, m: QPointF) -> QPointF:
        """Đỉnh đáy thứ hai: cách đỉnh cân bằng cạnh bên, theo hướng con trỏ."""
        a, b = self._clicks
        r = _dist(a, b)
        d = _dist(a, m) or 1.0
        return QPointF(a.x() + (m.x() - a.x()) * r / d,
                       a.y() + (m.y() - a.y()) * r / d)

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate(); self.activate(); return
        _, pos = self.scene.snap(pos)
        clicks = getattr(self, "_clicks", [])
        self._clicks = clicks
        if len(clicks) == 1 and _dist(clicks[0], pos) < 5:
            return
        if len(clicks) < 2:
            clicks.append(QPointF(pos))
            self.tm.status_hint.emit(
                "Tam giác cân: click đỉnh đáy thứ nhất" if len(clicks) == 1 else
                "Tam giác cân: click đỉnh đáy thứ hai (di chuột để chỉnh góc ở đỉnh)")
            return
        c = self._third(pos)
        if _dist(c, clicks[1]) < 3:
            return
        self._build([clicks[0], clicks[1], c])
        self._clicks = []
        self._remove_ghost()

    def _build(self, pts: list):
        vertices = [PointItem(p) for p in pts]
        edges = [SegmentItem(vertices[k], vertices[(k + 1) % 3]) for k in range(3)]
        item = ShapeItem(vertices, self.shape_label, kind=self.name, edges=edges)
        self.history.push_add_batch(self.scene, vertices + [item] + edges)
        self.tm.status_hint.emit(
            "✓ Tam giác cân — kéo đỉnh đáy để đổi góc; "
            "chuột phải vào tam giác (công cụ Chọn) để nhập số đo góc")

    def move(self, pos: QPointF, modifiers):
        clicks = getattr(self, "_clicks", [])
        if not clicks:
            return
        _, pos = self.scene.snap(pos)
        if len(clicks) == 1:
            self._update_ghost([clicks[0], pos])
        else:
            self._update_ghost([clicks[0], clicks[1], self._third(pos)])

    def release(self, pos: QPointF, button):
        pass


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
