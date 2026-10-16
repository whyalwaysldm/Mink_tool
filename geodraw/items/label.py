from PyQt6.QtWidgets import QGraphicsTextItem, QGraphicsItem
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCore import QPointF
from .base import GeoItem


class LabelItem(GeoItem):

    def __init__(self, text: str, pos: QPointF, color=None, font_size=12):
        super().__init__(color)
        self._text_item = QGraphicsTextItem(text)
        font = QFont("Times New Roman", font_size)
        self._text_item.setFont(font)
        self._text_item.setDefaultTextColor(color or QColor(30, 30, 30))
        self._text_item.setParentItem(self)
        self.setPos(pos)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(5)

    def set_text(self, text: str):
        self._text_item.setPlainText(text)

    def boundingRect(self):
        return self._text_item.boundingRect()

    def paint(self, painter, option, widget=None):
        pass  # text item draws itself
