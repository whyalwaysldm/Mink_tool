from abc import abstractmethod
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QColor, QPainterPath, QPainterPathStroker
from PyQt6.QtCore import Qt


def stroke_shape(path: QPainterPath, width: float = 10.0) -> QPainterPath:
    """Vùng click là dải mỏng dọc theo nét (không phải cả khung bao)."""
    stroker = QPainterPathStroker()
    stroker.setWidth(width)
    return stroker.createStroke(path)


class GeoItem(QGraphicsItem):
    """Abstract base for all geometry items."""

    DEFAULT_COLOR  = QColor(30, 30, 30)
    # Opacity khi item ở trạng thái "ẩn" — đủ mờ để nhận ra nhưng vẫn click được
    HIDDEN_OPACITY = 0.15

    def __init__(self, color=None, stroke_width=None):
        super().__init__()
        self.color: QColor = color or QColor(self.DEFAULT_COLOR)
        if stroke_width is None:
            from core.style_manager import get_style_manager
            stroke_width = get_style_manager().stroke_width
        self.stroke_width: float = stroke_width
        self._is_hidden: bool = False
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

    # ── Ẩn / Hiện ─────────────────────────────────────────────────────────

    def set_hidden(self, hidden: bool):
        """Ẩn (opacity thấp, vẫn click được) hoặc hiện trở lại."""
        self._is_hidden = hidden
        self.setOpacity(self.HIDDEN_OPACITY if hidden else 1.0)

    # ── Stubs ─────────────────────────────────────────────────────────────

    def itemChange(self, change, value):
        return super().itemChange(change, value)

    @abstractmethod
    def boundingRect(self):
        pass

    @abstractmethod
    def paint(self, painter, option, widget=None):
        pass
