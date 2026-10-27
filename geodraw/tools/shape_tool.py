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


# ── Vẽ bằng click vào các đỉnh ─────────────────────────────────────────────

def _sub(a: QPointF, b: QPointF) -> QPointF:
    return QPointF(a.x() - b.x(), a.y() - b.y())


def _cross(u: QPointF, v: QPointF) -> float:
    return u.x() * v.y() - u.y() * v.x()


def _height(a: QPointF, b: QPointF, m: QPointF) -> float:
    """Khoảng cách từ m tới đường thẳng AB."""
    return abs(_cross(_sub(b, a), _sub(m, a))) / (_dist(a, b) or 1.0)


def _normal(a: QPointF, b: QPointF, m: QPointF) -> QPointF:
    """Vector đơn vị vuông góc với AB, hướng về phía con trỏ m."""
    u = _sub(b, a)
    L = _dist(a, b) or 1.0
    n = QPointF(-u.y() / L, u.x() / L)
    return n if _cross(u, _sub(m, a)) >= 0 else QPointF(-n.x(), -n.y())


def _regular_on_side(a: QPointF, b: QPointF, m: QPointF, n: int) -> list:
    """Đa giác đều n cạnh có cạnh AB, nằm về phía con trỏ m."""
    sign = 1.0 if _cross(_sub(b, a), _sub(m, a)) >= 0 else -1.0
    th = sign * 2 * math.pi / n
    ux, uy = b.x() - a.x(), b.y() - a.y()
    pts = [QPointF(a), QPointF(b)]
    for k in range(1, n - 1):
        c, s = math.cos(th * k), math.sin(th * k)
        last = pts[-1]
        pts.append(QPointF(last.x() + ux * c - uy * s,
                           last.y() + ux * s + uy * c))
    return pts


class _ClickShapeTool(PresetShapeTool):
    """
    Hình vẽ bằng các click: n_clicks − 1 click đặt đỉnh, click cuối chọn phần
    còn lại (phía đặt hình / độ dài cạnh / đỉnh cuối) — các đỉnh còn lại tự
    đặt theo đúng tính chất của hình, xem _vertices.
    """
    n_clicks = 3
    hints: tuple = ()            # gợi ý trước mỗi click
    done_hint = ""

    def activate(self):
        super().activate()
        self._clicks: list = []
        self.tm.status_hint.emit(self.hints[0])

    def deactivate(self):
        super().deactivate()
        self._clicks = []

    def _vertices(self, m: QPointF):
        """Mọi đỉnh của hình khi click cuối ở m; None nếu chưa hợp lệ."""
        raise NotImplementedError

    def _valid_click(self, pos: QPointF) -> bool:
        clicks = self._clicks
        if any(_dist(c, pos) < 5 for c in clicks):
            return False
        # Đỉnh thứ ba trở đi không được thẳng hàng với cạnh đầu
        return len(clicks) < 2 or _height(clicks[0], clicks[1], pos) >= 3

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate(); self.activate(); return
        _, pos = self.scene.snap(pos)
        clicks = getattr(self, "_clicks", [])
        self._clicks = clicks
        if len(clicks) < self.n_clicks - 1:
            if self._valid_click(pos):
                clicks.append(QPointF(pos))
                self.tm.status_hint.emit(self.hints[len(clicks)])
            return
        pts = self._vertices(pos)
        if not pts:
            return
        self._build(pts)
        self._clicks = []
        self._remove_ghost()
        self.tm.status_hint.emit(
            self.done_hint or f"✓ {self.shape_label} — kéo đỉnh để đổi cỡ / xoay")

    def _build(self, pts: list):
        vertices = [PointItem(p) for p in pts]
        n = len(vertices)
        edges = [SegmentItem(vertices[k], vertices[(k + 1) % n]) for k in range(n)]
        item = ShapeItem(vertices, self.shape_label, kind=self.name, edges=edges)
        self.history.push_add_batch(self.scene, vertices + [item] + edges)

    def move(self, pos: QPointF, modifiers):
        clicks = getattr(self, "_clicks", [])
        if not clicks:
            return
        _, pos = self.scene.snap(pos)
        if len(clicks) == self.n_clicks - 1:
            pts = self._vertices(pos)
            if pts:
                self._update_ghost(pts)
                return
        self._update_ghost(clicks + [pos])

    def release(self, pos: QPointF, button):
        pass


class _RegularPolygonTool(_ClickShapeTool):
    """Đa giác đều: click 2 đỉnh của một cạnh, rồi click về phía đặt hình."""
    sides = 3

    @property
    def hints(self):
        return (f"{self.shape_label}: click đỉnh thứ nhất",
                f"{self.shape_label}: click đỉnh thứ hai",
                f"{self.shape_label}: click về phía muốn đặt hình")

    def _vertices(self, m):
        a, b = self._clicks
        if _height(a, b, m) < 1:
            return None
        return _regular_on_side(a, b, m, self.sides)


class RectangleTool(_ClickShapeTool):
    name = "rectangle"
    shape_label = "Hình chữ nhật"
    hints = ("Hình chữ nhật: click đỉnh thứ nhất",
             "Hình chữ nhật: click đỉnh thứ hai",
             "Hình chữ nhật: click để chọn độ dài cạnh còn lại")

    def _vertices(self, m):
        a, b = self._clicks
        h = _height(a, b, m)
        if h < 3:
            return None
        n = _normal(a, b, m)
        off = QPointF(n.x() * h, n.y() * h)
        return [a, b, b + off, a + off]


class SquareTool(_RegularPolygonTool):
    name = "square"
    shape_label = "Hình vuông"
    sides = 4


class EquilateralTriangleTool(_RegularPolygonTool):
    name = "equilateral_triangle"
    shape_label = "Tam giác đều"
    sides = 3


class RightTriangleTool(_ClickShapeTool):
    """Góc vuông tại đỉnh 1; click 3 chọn độ dài cạnh góc vuông thứ hai."""
    name = "right_triangle"
    shape_label = "Tam giác vuông"
    hints = ("Tam giác vuông: click đỉnh góc vuông",
             "Tam giác vuông: click đỉnh thứ hai",
             "Tam giác vuông: click để chọn độ dài cạnh góc vuông còn lại")

    def _vertices(self, m):
        a, b = self._clicks
        h = _height(a, b, m)
        if h < 3:
            return None
        n = _normal(a, b, m)
        return [a, b, QPointF(a.x() + n.x() * h, a.y() + n.y() * h)]


class IsoscelesRightTriangleTool(_ClickShapeTool):
    """Góc vuông tại đỉnh 1, 2 cạnh góc vuông bằng nhau; click 3 chọn phía."""
    name = "isosceles_right_triangle"
    shape_label = "Tam giác vuông cân"
    hints = ("Tam giác vuông cân: click đỉnh góc vuông",
             "Tam giác vuông cân: click đỉnh thứ hai",
             "Tam giác vuông cân: click về phía đặt đỉnh thứ ba")

    def _vertices(self, m):
        a, b = self._clicks
        n = _normal(a, b, m)
        r = _dist(a, b)
        return [a, b, QPointF(a.x() + n.x() * r, a.y() + n.y() * r)]


class RhombusTool(_ClickShapeTool):
    """Click 2 đỉnh (một cạnh), click 3 chọn hướng cạnh kề (cùng độ dài)."""
    name = "rhombus"
    shape_label = "Hình thoi"
    hints = ("Hình thoi: click đỉnh thứ nhất",
             "Hình thoi: click đỉnh thứ hai",
             "Hình thoi: click để chọn hướng cạnh kề (góc của hình thoi)")

    def _vertices(self, m):
        a, b = self._clicks
        d = _dist(b, m)
        if d < 1e-6:
            return None
        r = _dist(a, b)
        c = QPointF(b.x() + (m.x() - b.x()) * r / d,
                    b.y() + (m.y() - b.y()) * r / d)
        if _height(a, b, c) < 3:
            return None               # gần thẳng hàng → hình dẹt
        return [a, b, c, a + c - b]


class ParallelogramTool(_ClickShapeTool):
    """Click 3 đỉnh liên tiếp; đỉnh thứ tư tự đặt."""
    name = "parallelogram"
    shape_label = "Hình bình hành"
    hints = ("Hình bình hành: click đỉnh thứ nhất",
             "Hình bình hành: click đỉnh thứ hai",
             "Hình bình hành: click đỉnh thứ ba (đỉnh thứ tư tự đặt)")

    def _vertices(self, m):
        a, b = self._clicks
        if _height(a, b, m) < 3:
            return None
        return [a, b, m, a + m - b]


class IsoscelesTriangleTool(_ClickShapeTool):
    """
    Tam giác cân vẽ bằng 3 click:
      1. đỉnh (đỉnh cân)   2. đỉnh đáy thứ nhất
      3. đỉnh đáy thứ hai — tự đặt sao cho 2 cạnh bên bằng nhau,
         hướng theo con trỏ (góc ở đỉnh lớn / nhỏ tùy chỗ click).
    """
    name = "isosceles_triangle"
    shape_label = "Tam giác cân"
    hints = ("Tam giác cân: click đỉnh (đỉnh cân)",
             "Tam giác cân: click đỉnh đáy thứ nhất",
             "Tam giác cân: click đỉnh đáy thứ hai (di chuột để chỉnh góc ở đỉnh)")
    done_hint = ("✓ Tam giác cân — kéo đỉnh đáy để đổi góc; "
                 "chuột phải vào tam giác (công cụ Chọn) để nhập số đo góc")

    def _vertices(self, m):
        """Đỉnh đáy thứ hai: cách đỉnh cân bằng cạnh bên, theo hướng con trỏ."""
        a, b = self._clicks
        r = _dist(a, b)
        d = _dist(a, m) or 1.0
        c = QPointF(a.x() + (m.x() - a.x()) * r / d,
                    a.y() + (m.y() - a.y()) * r / d)
        if _dist(c, b) < 3:
            return None
        return [a, b, c]


class TrapezoidTool(_ClickShapeTool):
    """Click 2 đỉnh của đáy, đỉnh thứ ba, rồi đỉnh thứ tư (trên đường song song đáy)."""
    name = "trapezoid"
    shape_label = "Hình thang"
    n_clicks = 4
    hints = ("Hình thang: click đỉnh thứ nhất của đáy",
             "Hình thang: click đỉnh thứ hai của đáy",
             "Hình thang: click đỉnh thứ ba",
             "Hình thang: click đỉnh thứ tư (nằm trên đường song song với đáy)")

    def _vertices(self, m):
        a, b, c = self._clicks
        u = _sub(b, a)
        L2 = (u.x() ** 2 + u.y() ** 2) or 1.0
        t = ((m.x() - c.x()) * u.x() + (m.y() - c.y()) * u.y()) / L2
        if t > -0.02:
            return None               # đỉnh thứ tư phải lùi về phía đỉnh thứ nhất
        return [a, b, c, QPointF(c.x() + u.x() * t, c.y() + u.y() * t)]


class RegularHexagonTool(_RegularPolygonTool):
    name = "hexagon"
    shape_label = "Lục giác đều"
    sides = 6


class RegularPentagonTool(_RegularPolygonTool):
    name = "pentagon"
    shape_label = "Ngũ giác đều"
    sides = 5


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
