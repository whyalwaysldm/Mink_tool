from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsItem
from PyQt6.QtGui import QFont, QColor, QPen
from PyQt6.QtCore import QPointF, Qt
from .base import GeoItem

MIN_FONT_SIZE = 6
MAX_FONT_SIZE = 96


class LabelItem(GeoItem):

    def __init__(self, text: str, pos: QPointF, color=None,
                 font_size=None, font_family=None):
        super().__init__(color)
        if font_size is None or font_family is None:
            from config.app_settings import AppSettings
            s = AppSettings.load()
            font_size = font_size or s.label_font_size
            font_family = font_family or s.label_font_family
        self._font_family = font_family
        self._font_size = int(font_size)
        self._text_item = QGraphicsTextItem(text)
        self._text_item.setDefaultTextColor(color or QColor(30, 30, 30))
        self._text_item.setParentItem(self)
        # Text con không nhận chuột — mọi thao tác đi qua LabelItem
        self._text_item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self._apply_font()
        self.setPos(pos)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(5)

    # ── Nội dung / kiểu chữ ──────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._text_item.toPlainText()

    @property
    def font_family(self) -> str:
        return self._font_family

    @property
    def font_size(self) -> int:
        return self._font_size

    def set_text(self, text: str):
        self.prepareGeometryChange()
        self._text_item.setPlainText(text)

    def _apply_font(self):
        self.prepareGeometryChange()
        self._text_item.setFont(QFont(self._font_family, self._font_size))

    def style_state(self) -> tuple:
        """(text, family, size) — dùng cho undo/redo."""
        return (self.text, self._font_family, self._font_size)

    def apply_style_state(self, state: tuple):
        text, family, size = state
        self._font_family = family
        self._font_size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, int(size)))
        self.set_text(text)
        self._apply_font()

    # ── Vẽ ───────────────────────────────────────────────────────────────

    def boundingRect(self):
        return self._text_item.boundingRect()

    def paint(self, painter, option, widget=None):
        # Text con tự vẽ; ở đây chỉ vẽ khung khi đang được chọn
        if self.isSelected():
            r = self.boundingRect()
            painter.fillRect(r, QColor(0, 120, 215, 28))
            pen = QPen(QColor(0, 120, 215), 1.0, Qt.PenStyle.DashLine)
            pen.setCosmetic(True)
            painter.setPen(pen)
            painter.drawRect(r)
