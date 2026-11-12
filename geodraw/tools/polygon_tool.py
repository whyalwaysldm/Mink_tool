from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsPolygonItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.shape import ShapeItem
from items.segment import SegmentItem


class PolygonTool(BaseTool):
    name = "polygon"
    _max_pts = None  # None = unlimited (close on double-click/Enter)

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._pts: list = []
        self._pts_new: list = []
        self._ghost = None

    def activate(self):
        self._pts = []
        self._pts_new = []
        self._remove_ghost()

    def deactivate(self):
        for pt, is_new in zip(self._pts, self._pts_new):
            if is_new and pt.scene():
                self.scene.removeItem(pt)
        self._pts = []
        self._pts_new = []
        self._remove_ghost()

    def _remove_ghost(self):
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._ghost = None

    def _update_ghost(self, cursor_pos: QPointF = None):
        scene_pts = [p.scenePos() for p in self._pts]
        if cursor_pos:
            scene_pts.append(cursor_pos)
        if len(scene_pts) < 2:
            return
        if self._ghost is None:
            self._ghost = QGraphicsPolygonItem()
            self._ghost.setPen(QPen(QColor(0, 120, 215, 140), 1.5,
                                    Qt.PenStyle.DashLine))
            self._ghost.setBrush(QBrush(Qt.BrushStyle.NoBrush))
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)
        self._ghost.setPolygon(QPolygonF(scene_pts))

    def _finish(self):
        if len(self._pts) < 3:
            self.deactivate()
            self.activate()
            return
        # Mỗi cạnh là một đoạn riêng → click 1 lần chọn cạnh, double-click
        # mới chọn cả hình (như hình mẫu); kéo đỉnh tự do
        n = len(self._pts)
        edges = [SegmentItem(self._pts[k], self._pts[(k + 1) % n])
                 for k in range(n)]
        label = "tam giác" if n == 3 else "đa giác"
        poly = ShapeItem(self._pts, label, kind=self.name, edges=edges)
        new_pts = [p for p, is_new in zip(self._pts, self._pts_new) if is_new]
        self.history.push_add_batch(self.scene, new_pts + [poly] + edges)
        self._pts = []
        self._pts_new = []
        self._remove_ghost()

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        snapped_item, snapped_pos = self.scene.snap(pos)
        if snapped_item and self._pts and snapped_item is self._pts[0]:
            self._finish()
            return
        if snapped_item:
            pt, is_new = snapped_item, False
        else:
            pt = self.scene.new_point(snapped_pos)
            self.scene.addItem(pt)
            is_new = True
        self._pts.append(pt)
        self._pts_new.append(is_new)
        if self._max_pts and len(self._pts) >= self._max_pts:
            self._finish()

    def move(self, pos: QPointF, modifiers):
        if self._pts:
            _, snapped = self.scene.snap(pos)
            self._update_ghost(snapped)

    def double_click(self, pos: QPointF):
        self._finish()

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self._finish()
        elif key == Qt.Key.Key_Escape:
            self.deactivate()
            self.activate()

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)


class TriangleTool(PolygonTool):
    name = "triangle"
    _max_pts = 3


class TriangleAltitudesTool(TriangleTool):
    """
    Tam giác + 3 đường cao: click 3 đỉnh → tam giác, 3 chân đường cao, 3 đường
    cao, ký hiệu góc vuông và trực tâm H. Kéo đỉnh → mọi thứ cập nhật theo.
    Tam giác tù: cạnh được kéo dài tới chân đường cao, đường cao kéo dài tới H.
    """
    name = "triangle_altitudes"

    def activate(self):
        super().activate()
        self.tm.status_hint.emit("Tam giác + 3 đường cao: click 3 đỉnh")

    def _finish(self):
        if len(self._pts) < 3:
            super()._finish()
            return
        from items.constructed import FootPointItem
        from items.on_curve import IntersectionPointItem, anchor_points
        from items.marks import RightAngleMarkItem
        pts = list(self._pts)
        self.history.stack.beginMacro("Tam giác + 3 đường cao")   # 1 bước hoàn tác
        super()._finish()
        extra, alts = [], []
        for k in range(3):
            a, b, c = pts[k], pts[(k + 1) % 3], pts[(k + 2) % 3]
            foot = FootPointItem(a, b, c)
            alt = SegmentItem(a, foot)
            alts.append(alt)
            # Cạnh kéo dài tới chân đường cao (trùng cạnh khi chân nằm trong cạnh)
            far = b if (b.scenePos() - foot.scenePos()).manhattanLength() > \
                (c.scenePos() - foot.scenePos()).manhattanLength() else c
            extra += [foot, alt, SegmentItem(foot, b), SegmentItem(foot, c),
                      RightAngleMarkItem(foot, a, far)]
        for it in extra:
            self.scene.addItem(it)
        # Trực tâm: giao của 2 đường cao (kéo dài nếu cần)
        from utils.snap_engine import curves_of, intersect_curves
        ip = intersect_curves(curves_of(alts[0])[0], curves_of(alts[1])[0],
                              extend=True)
        if ip:
            h_pos = ip[0]
            anchors = anchor_points(self.scene, alts[0])
            anchors += [p for p in anchor_points(self.scene, alts[1])
                        if p not in anchors]
            H = IntersectionPointItem(alts[0], 0, alts[1], 0, h_pos, anchors)
            self.scene.addItem(H)
            extra.append(H)
            for p in pts:                           # đường cao kéo dài tới H
                seg = SegmentItem(H, p)
                self.scene.addItem(seg)
                extra.append(seg)
        self.history.push_add_batch(self.scene, extra)
        self.history.stack.endMacro()
        self.tm.status_hint.emit(
            "✓ Tam giác + 3 đường cao, trực tâm H — kéo đỉnh, mọi thứ tự cập nhật")
