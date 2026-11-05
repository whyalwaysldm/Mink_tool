from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QPen, QBrush, QColor, QPainterPath
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsPathItem
from .base_tool import BaseTool
from items.point import PointItem
from items.segment import SegmentItem
from items.circle import CircleItem
from items.circumcircle import CircumcircleItem
from items.arc import ArcItem
from items.on_curve import anchor_points
from items.tangent_point import TangentPointItem, tangent_point
from utils.snap_engine import curves_of, _nearest_on_curve

_CIRCLES = (CircleItem, CircumcircleItem, ArcItem)


class TangentLinesTool(BaseTool):
    """
    Hai tiếp tuyến từ một điểm nằm ngoài đường tròn.

    • Click tâm, click điểm xác định bán kính, rồi click điểm nằm ngoài
      → vẽ cả đường tròn, điểm ngoài, 2 tiếp điểm và 2 tiếp tuyến.
    • Hoặc click vào một đường tròn có sẵn, rồi click điểm nằm ngoài.
    • Hoặc Ctrl + click 1 điểm và 1 đường tròn (công cụ Chọn) rồi bấm Y.
    Kéo tâm, điểm bán kính hoặc điểm ngoài → tiếp điểm, tiếp tuyến đi theo.
    """
    name = "tangent_lines"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._circle = None           # đường tròn có sẵn đã chọn
        self._center = None           # tâm (khi vẽ đường tròn mới)
        self._radius_pt = None
        self._new: list = []          # đối tượng mới, chưa vào lịch sử
        self._ghost_circle = None
        self._ghost_lines = None

    # ── Lifecycle ─────────────────────────────────────────────────────

    def activate(self):
        self._clear_state()
        sel = self.scene.selectedItems()
        pts = [it for it in sel if isinstance(it, PointItem)]
        circles = [it for it in sel if isinstance(it, _CIRCLES)]
        if len(pts) == 1 and len(circles) == 1:
            self.scene.clearSelection()
            self._circle = circles[0]
            self._finish(pts[0])
            return
        self._hint()

    def deactivate(self):
        for it in self._new:
            if it.scene():
                self.scene.removeItem(it)
        if self._circle is not None and self._circle.scene():
            self._circle.setSelected(False)
        self._clear_state()

    def _clear_state(self):
        self._circle = self._center = self._radius_pt = None
        self._new = []
        self._remove_ghosts()

    def _hint(self):
        if self._circle is not None or self._radius_pt is not None:
            msg = "Tiếp tuyến: click điểm nằm ngoài đường tròn"
        elif self._center is not None:
            msg = "Tiếp tuyến: click để chọn bán kính đường tròn"
        else:
            msg = ("Tiếp tuyến: click tâm đường tròn (hoặc click vào một "
                   "đường tròn có sẵn)")
        self.tm.status_hint.emit(msg)

    # ── Ghost ─────────────────────────────────────────────────────────

    def _remove_ghosts(self):
        for g in (self._ghost_circle, self._ghost_lines):
            if g is not None and g.scene():
                g.scene().removeItem(g)
        self._ghost_circle = self._ghost_lines = None

    def _ghost_pen(self):
        pen = QPen(QColor(0, 120, 215, 150), 1.4, Qt.PenStyle.DashLine)
        pen.setCosmetic(True)
        return pen

    def _show_ghost_circle(self, c: QPointF, r: float):
        if self._ghost_circle is None:
            self._ghost_circle = QGraphicsEllipseItem()
            self._ghost_circle.setPen(self._ghost_pen())
            self._ghost_circle.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self._ghost_circle.setZValue(50)
            self.scene.addItem(self._ghost_circle)
        self._ghost_circle.setRect(c.x() - r, c.y() - r, 2 * r, 2 * r)

    def _show_ghost_lines(self, p: QPointF, curve: tuple):
        path = QPainterPath()
        for side in (1, -1):
            t = tangent_point(p, curve, side)
            if t is not None:
                path.moveTo(p)
                path.lineTo(t)
        if self._ghost_lines is None:
            self._ghost_lines = QGraphicsPathItem()
            self._ghost_lines.setPen(self._ghost_pen())
            self._ghost_lines.setZValue(50)
            self.scene.addItem(self._ghost_lines)
        self._ghost_lines.setPath(path)

    def _current_curve(self):
        """Curve đường tròn đã chọn / đang vẽ (tuple 'circle'), hoặc None."""
        if self._circle is not None:
            cs = curves_of(self._circle)
            return cs[0] if cs else None
        if self._radius_pt is not None:
            c, q = self._center.scenePos(), self._radius_pt.scenePos()
            r = ((q.x() - c.x()) ** 2 + (q.y() - c.y()) ** 2) ** 0.5
            return ('circle', c, r) if r > 0.5 else None
        return None

    # ── Events ────────────────────────────────────────────────────────

    def _circle_at(self, pos: QPointF):
        for it in self.scene.items():
            if isinstance(it, _CIRCLES) and it.isVisible():
                for c in curves_of(it):
                    if _nearest_on_curve(pos, c) is not None:
                        return it
        return None

    def _point_at(self, pos: QPointF):
        """Điểm có sẵn (bắt dính) hoặc điểm mới tại pos."""
        snapped, spos = self.scene.snap(pos)
        if isinstance(snapped, PointItem):
            return snapped
        pt = self.scene.new_point(spos)
        self.scene.addItem(pt)
        self._new.append(pt)
        return pt

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        snapped, _ = self.scene.snap(pos)
        if self._circle is None and self._center is None:
            circle = None if isinstance(snapped, PointItem) else self._circle_at(pos)
            if circle is not None:
                self._circle = circle
                circle.setSelected(True)
            else:
                self._center = self._point_at(pos)
            self._hint()
            return
        if self._center is not None and self._radius_pt is None:
            pt = self._point_at(pos)
            if pt is self._center:
                return
            self._radius_pt = pt
            circle = CircleItem(self._center, pt)
            self.scene.addItem(circle)
            self._new.append(circle)
            self._circle = circle
            self._remove_ghosts()
            self._hint()
            return
        # Bước cuối: điểm nằm ngoài
        curve = self._current_curve()
        p = self._point_at(pos)
        if curve is None or tangent_point(p.scenePos(), curve, 1) is None:
            if p in self._new:
                self._new.remove(p)
                self.scene.removeItem(p)
            self.tm.status_hint.emit(
                "Tiếp tuyến: điểm phải nằm ngoài đường tròn")
            return
        self._finish(p)

    def _finish(self, p: PointItem):
        circle = self._circle
        curve = self._current_curve()
        if curve is None or tangent_point(p.scenePos(), curve, 1) is None:
            self.tm.status_hint.emit("Tiếp tuyến: điểm phải nằm ngoài đường tròn")
            self._circle = None
            return
        anchors = anchor_points(self.scene, circle)
        items = list(self._new)       # tâm / bán kính / điểm ngoài mới tạo
        for side in (1, -1):
            t = TangentPointItem(p, circle, side, anchors)
            items += [t, SegmentItem(p, t)]
        for it in items:
            if it.scene() is None:
                self.scene.addItem(it)
        self.history.push_add_batch(self.scene, items)
        if circle.scene():
            circle.setSelected(False)
        self._new = []
        self._clear_state()
        self.tm.status_hint.emit(
            "✓ Đã vẽ 2 tiếp tuyến — kéo tâm, bán kính hoặc điểm ngoài, "
            "tiếp tuyến tự cập nhật")

    def move(self, pos: QPointF, modifiers):
        _, spos = self.scene.snap(pos)
        if self._center is not None and self._radius_pt is None:
            c = self._center.scenePos()
            r = ((spos.x() - c.x()) ** 2 + (spos.y() - c.y()) ** 2) ** 0.5
            self._show_ghost_circle(c, r)
            return
        curve = self._current_curve()
        if curve is not None:
            self._show_ghost_lines(spos, curve)

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Escape:
            self.deactivate()
            self.activate()
