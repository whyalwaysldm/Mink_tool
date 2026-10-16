from PyQt6.QtCore import QObject, QEvent
from PyQt6.QtGui import QTabletEvent


class TabletState:
    """Singleton holding current stylus state."""
    pressure: float = 0.5
    is_eraser: bool = False
    _prev_tool: str = "select"


_state = TabletState()


def get_state() -> TabletState:
    return _state


class EraserAutoSwitch(QObject):
    """App-level event filter: auto-switches to erase tool when eraser detected."""

    def __init__(self, tool_manager, parent=None):
        super().__init__(parent)
        self._tm = tool_manager
        self._switched = False

    def eventFilter(self, obj, event):
        t = event.type()
        if t in (QEvent.Type.TabletPress, QEvent.Type.TabletMove,
                 QEvent.Type.TabletRelease):
            ev: QTabletEvent = event
            is_eraser = (ev.pointerType() ==
                         QTabletEvent.PointerType.Eraser)
            _state.pressure = ev.pressure()
            _state.is_eraser = is_eraser

            if t == QEvent.Type.TabletPress:
                if is_eraser and not self._switched:
                    _state._prev_tool = self._tm.current_name
                    self._tm.activate("erase")
                    self._switched = True
                elif not is_eraser and self._switched:
                    self._tm.activate(_state._prev_tool)
                    self._switched = False

            if t == QEvent.Type.TabletRelease and self._switched and not is_eraser:
                self._tm.activate(_state._prev_tool)
                self._switched = False

        return False
