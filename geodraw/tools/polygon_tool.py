from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtWidgets import QGraphicsPolygonItem
from PyQt6.QtGui import QPen, QBrush, QPolygonF, QColor
from .base_tool import BaseTool
from items.point import PointItem
from items.polygon import PolygonItem, TriangleItem


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
            self._ghost.setBrush(QBrush(QColor(0, 120, 215, 20)))
            self._ghost.setZValue(50)
            self.scene.addItem(self._ghost)
        self._ghost.setPolygon(QPolygonF(scene_pts))

    def _finish(self):
        if len(self._pts) < 3:
            self.deactivate()
            self.activate()
            return
        cls = TriangleItem if len(self._pts) == 3 and isinstance(self, TriangleTool) \
              else PolygonItem
        poly = PolygonItem(self._pts)
        self.scene.addItem(poly)
        to_record = [self._pts[i] for i, n in enumerate(self._pts_new) if n] + [poly]
        if len(to_record) == 1:
            self.history.push_add(self.scene, to_record[0])
        else:
            self.history.push_add_batch(self.scene, to_record)
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
