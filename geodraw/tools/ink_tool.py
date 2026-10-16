from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QColor
from .base_tool import BaseTool
from items.ink_stroke import InkStrokeItem
from utils.tablet import get_state


class InkTool(BaseTool):
    name = "ink"

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._stroke: InkStrokeItem = None
        self._drawing = False
        self.ink_color = QColor(30, 30, 30)
        self.base_width = 3.0

    def activate(self):
        self._stroke = None
        self._drawing = False

    def deactivate(self):
        if self._stroke and not self._drawing:
            pass
        self._stroke = None
        self._drawing = False

    def _begin(self, pos: QPointF, pressure: float):
        self._stroke = InkStrokeItem(color=self.ink_color,
                                     base_width=self.base_width)
        self.scene.addItem(self._stroke)
        self._stroke.add_sample(pos, pressure)
        self._drawing = True

    def _end(self):
        if self._stroke:
            self._stroke.finalize()
            self.history.push_add(self.scene, self._stroke)
        self._stroke = None
        self._drawing = False

    # ── tablet (pressure-aware) ──────────────────────────────────────────
    def tablet_press(self, pos: QPointF, pressure: float, button):
        self._begin(pos, pressure)

    def tablet_move(self, pos: QPointF, pressure: float):
        if self._drawing and self._stroke:
            self._stroke.add_sample(pos, pressure)

    def tablet_release(self, pos: QPointF, pressure: float):
        self._end()

    # ── mouse fallback ───────────────────────────────────────────────────
    def press(self, pos: QPointF, button, modifiers):
        if button == Qt.MouseButton.LeftButton:
            self._begin(pos, 0.6)

    def move(self, pos: QPointF, modifiers):
        if self._drawing and self._stroke:
            self._stroke.add_sample(pos, 0.6)

    def release(self, pos: QPointF, button):
        if button == Qt.MouseButton.LeftButton:
            self._end()
