from PyQt6.QtCore import Qt, QPointF
from .base_tool import BaseTool
from items.point import PointItem
from items.arc import ArcItem


class ArcTool(BaseTool):
    name = "arc"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._pts: list = []
        self._pts_new: list = []
        self._ghost: ArcItem = None

    def activate(self):
        self._pts = []
        self._pts_new = []
        self._ghost = None

    def deactivate(self):
        for pt, is_new in zip(self._pts, self._pts_new):
            if is_new and pt.scene():
                self.scene.removeItem(pt)
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        self._pts = []
        self._pts_new = []
        self._ghost = None

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            self.deactivate()
            self.activate()
            return
        snapped_item, snapped_pos = self.scene.snap(pos)
        pt = snapped_item or self.scene.new_point(snapped_pos)
        is_new = snapped_item is None
        if is_new:
            self.scene.addItem(pt)
        self._pts.append(pt)
        self._pts_new.append(is_new)

        if len(self._pts) == 3:
            self._finish()

    def _finish(self):
        arc = ArcItem(self._pts[0], self._pts[1], self._pts[2])
        self.scene.addItem(arc)
        if self._ghost and self._ghost.scene():
            self.scene.removeItem(self._ghost)
        to_record = ([p for p, n in zip(self._pts, self._pts_new) if n] + [arc])
        if len(to_record) == 1:
            self.history.push_add(self.scene, to_record[0])
        else:
            self.history.push_add_batch(self.scene, to_record)
        self._pts = []
        self._pts_new = []
        self._ghost = None
