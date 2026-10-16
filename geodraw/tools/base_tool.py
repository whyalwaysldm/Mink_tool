from PyQt6.QtCore import Qt, QPointF
from PyQt6.QtGui import QCursor


class BaseTool:
    _cursor_shape = Qt.CursorShape.CrossCursor
    name: str = "base"

    @property
    def cursor(self):
        return QCursor(self._cursor_shape)

    def __init__(self, scene, history, tool_manager):
        self.scene = scene
        self.history = history
        self.tm = tool_manager

    def activate(self):
        pass

    def deactivate(self):
        pass

    def press(self, pos: QPointF, button, modifiers):
        pass

    def move(self, pos: QPointF, modifiers):
        pass

    def release(self, pos: QPointF, button):
        pass

    def double_click(self, pos: QPointF):
        pass

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_Escape:
            self.deactivate()
            self.activate()

    # tablet overrides — default delegates to mouse methods
    def tablet_press(self, pos: QPointF, pressure: float, button):
        self.press(pos, button, Qt.KeyboardModifier.NoModifier)

    def tablet_move(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)

    def tablet_release(self, pos: QPointF, pressure: float):
        self.release(pos, Qt.MouseButton.LeftButton)

    def hover(self, pos: QPointF, pressure: float):
        self.move(pos, Qt.KeyboardModifier.NoModifier)
