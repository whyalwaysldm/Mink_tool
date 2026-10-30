from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QColor
from PyQt6.QtWidgets import QGraphicsEllipseItem
from .base_tool import BaseTool
from items.segment import SegmentItem
from items.line import LineItem, RayItem
from items.circle import CircleItem
from items.circumcircle import CircumcircleItem
from items.arc import ArcItem
from items.bisector_ray import BisectorRayItem
from items.on_curve import anchor_points
from items.tangent_circle import TangentCenterItem, TangentRadiusPointItem
from utils.snap_engine import curves_of, _nearest_on_curve
from utils.tangent import tangent_circles

_LINES = (SegmentItem, LineItem, RayItem, BisectorRayItem)
_CIRCLES = (CircleItem, CircumcircleItem, ArcItem)


class TangentCircleTool(BaseTool):
    """
    Đường tròn tiếp xúc 2 đường thẳng và 1 đường tròn.

    • Công cụ Chọn: Ctrl + click 3 đường, rồi bấm phím tắt / nút công cụ.
    • Hoặc bật công cụ rồi click lần lượt 3 đường.
    Có nhiều nghiệm → hiện các đường tròn nét đứt, click vào cái muốn vẽ.
    """
    name = "tangent_circle"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._objs: list = []
        self._sols: list = []
        self._ghosts: list = []

    # ── Lifecycle ─────────────────────────────────────────────────────

    def activate(self):
        self._objs, self._sols = [], []
        sel = self.scene.selectedItems()
        objs = [it for it in sel if isinstance(it, _LINES + _CIRCLES)]
        if len(objs) == 3 and self._valid(objs):
            self._objs = objs
            self._solve()
        else:
            self.scene.clearSelection()
            self.tm.status_hint.emit(
                "Đường tròn tiếp xúc: click 2 đường thẳng và 1 đường tròn "
                "(hoặc Ctrl + click 3 đường ở công cụ Chọn rồi bấm U)")

    def deactivate(self):
        self._remove_ghosts()
        for it in self._objs:
            if it.scene():
                it.setSelected(False)
        self._objs, self._sols = [], []

    def _remove_ghosts(self):
        for g in self._ghosts:
            if g.scene():
                g.scene().removeItem(g)
        self._ghosts = []

    # ── Chọn đường ────────────────────────────────────────────────────

    @staticmethod
    def _valid(objs: list) -> bool:
        lines = sum(isinstance(o, _LINES) for o in objs)
        return lines <= 2 and len(objs) - lines <= 1

    def _curve_at(self, pos: QPointF):
        best, best_d = None, 10.0
        for it in self.scene.items():
            if not isinstance(it, _LINES + _CIRCLES) or not it.isVisible():
                continue
            for c in curves_of(it):
                foot = _nearest_on_curve(pos, c)
                if foot is None:
                    continue
                d = (foot - pos).manhattanLength()
                if d < best_d:
                    best, best_d = it, d
        return best

    def _ordered(self) -> tuple:
        lines = [o for o in self._objs if isinstance(o, _LINES)]
        circle = next(o for o in self._objs if isinstance(o, _CIRCLES))
        return lines[0], lines[1], circle

    # ── Tìm nghiệm ────────────────────────────────────────────────────

    def _solve(self):
        l1, l2, c = self._ordered()
        curves = [curves_of(o) for o in (l1, l2, c)]
        self._sols = tangent_circles(curves[0][0], curves[1][0], curves[2][0]) \
            if all(curves) else []
        if not self._sols:
            self.tm.status_hint.emit(
                "Không có đường tròn nào tiếp xúc với 3 đường này")
            self._reset_objs()
        elif len(self._sols) == 1:
            self._create(self._sols[0])
        else:
            self._show_ghosts()
            self.tm.status_hint.emit(
                f"Có {len(self._sols)} đường tròn tiếp xúc — click vào đường "
                "tròn muốn vẽ  |  Esc để hủy")

    def _show_ghosts(self):
        self._remove_ghosts()
        for center, r in self._sols:
            g = QGraphicsEllipseItem(center.x() - r, center.y() - r, 2 * r, 2 * r)
            g.setZValue(50)
            self.scene.addItem(g)
            self._ghosts.append(g)
        self._highlight(None)

    def _highlight(self, idx):
        for k, g in enumerate(self._ghosts):
            on = k == idx
            pen = QPen(QColor(230, 120, 0, 230) if on else QColor(0, 120, 215, 130),
                       2.0 if on else 1.2, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            g.setPen(pen)

    def _nearest_sol(self, pos: QPointF):
        def gap(sol):
            c, r = sol
            d = ((pos.x() - c.x()) ** 2 + (pos.y() - c.y()) ** 2) ** 0.5
            return abs(d - r)
        return min(range(len(self._sols)), key=lambda k: gap(self._sols[k]))

    def _create(self, sol):
        l1, l2, c = self._ordered()
        anchors = []
        for host in (l1, l2, c):
            anchors += [p for p in anchor_points(self.scene, host)
                        if p not in anchors]
        center = TangentCenterItem(l1, l2, c, sol[0], sol[1], anchors)
        rp = TangentRadiusPointItem(center)
        circle = CircleItem(center, rp)
        self.history.push_add_batch(self.scene, [center, rp, circle])
        self._reset_objs()
        self.tm.status_hint.emit(
            "✓ Đã vẽ đường tròn tiếp xúc và tâm — tự cập nhật khi kéo hình")

    def _reset_objs(self):
        self._remove_ghosts()
        self.scene.clearSelection()
        self._objs, self._sols = [], []

    # ── Events ────────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self._reset_objs()
            self.activate()
            return
        if self._sols:
            self._create(self._sols[self._nearest_sol(pos)])
            return
        obj = self._curve_at(pos)
        if obj is None:
            self.tm.status_hint.emit(
                "Đường tròn tiếp xúc: hãy click vào đường thẳng hoặc đường tròn")
            return
        if obj in self._objs:
            self._objs.remove(obj)
            obj.setSelected(False)
        elif self._valid(self._objs + [obj]):
            self._objs.append(obj)
            obj.setSelected(True)
        else:
            self.tm.status_hint.emit(
                "Cần đúng 2 đường thẳng (đoạn / tia) và 1 đường tròn")
            return
        if len(self._objs) == 3:
            self._solve()
        else:
            self.tm.status_hint.emit(
                f"Đường tròn tiếp xúc: đã chọn {len(self._objs)}/3 đường")

    def move(self, pos: QPointF, modifiers):
        if self._sols and self._ghosts:
            self._highlight(self._nearest_sol(pos))

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Escape:
            self._reset_objs()
            self.activate()
