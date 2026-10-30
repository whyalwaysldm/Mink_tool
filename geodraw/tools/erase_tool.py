from PyQt6.QtCore import Qt, QPointF, QRectF
from .base_tool import BaseTool


ERASER_RADIUS = 16.0


class EraseTool(BaseTool):
    name = "erase"
    _cursor_shape = Qt.CursorShape.CrossCursor

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._erasing = False
        self._erased: list = []

    def activate(self):
        self._erasing = False
        self._erased = []

    def deactivate(self):
        self._commit()

    def _items_at(self, pos: QPointF) -> list:
        r = ERASER_RADIUS
        rect = QRectF(pos.x() - r, pos.y() - r, r * 2, r * 2)
        from items.point import PointItem
        items = []
        for it in self.scene.items(rect):
            if hasattr(it, 'color') and it not in self._erased:
                items.append(it)
        return items

    def _commit(self):
        if self._erased:
            from items.point_label import with_line_names
            self.history.push_remove(
                self.scene, with_line_names(self.scene, list(self._erased)))
        self._erased = []
        self._erasing = False

    def _erase_at(self, pos: QPointF):
        for it in self._items_at(pos):
            if it not in self._erased:
                self._erased.append(it)
                it.setOpacity(0.2)

    def press(self, pos: QPointF, button, modifiers):
        self._erasing = True
        self._erase_at(pos)

    def tablet_press(self, pos: QPointF, pressure: float, button):
        self._erasing = True
        self._erase_at(pos)

    def move(self, pos: QPointF, modifiers):
        if self._erasing:
            self._erase_at(pos)

    def tablet_move(self, pos: QPointF, pressure: float):
        if self._erasing:
            self._erase_at(pos)

    def release(self, pos: QPointF, button):
        self._commit()

    def tablet_release(self, pos: QPointF, pressure: float):
        self._commit()
