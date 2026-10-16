from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem

RADIUS = 3.5   # fallback cho code cũ; giá trị thực lấy từ StyleManager


class PointItem(GeoItem):

    def __init__(self, pos: QPointF, color=None):
        super().__init__(color)
        self.setPos(pos)
        self.label: str = ""          # tên điểm (A, B, C …) — dùng bởi PointLabelItem
        self._label_item = None       # ref tới PointLabelItem hiện tại (nếu có)
        self._dependents: list = []
        # Radius lấy từ StyleManager tại thời điểm tạo điểm
        from core.style_manager import get_style_manager
        self._radius: float = get_style_manager().point_radius
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setZValue(10)

    def center(self) -> QPointF:
        return self.scenePos()

    def add_dependent(self, item):
        if item not in self._dependents:
            self._dependents.append(item)

    def remove_dependent(self, item):
        if item in self._dependents:
            self._dependents.remove(item)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            for dep in self._dependents:
                # Constrained points (MidpointItem, CircumcenterItem…) reposition first
                if hasattr(dep, 'update_position'):
                    dep.update_position()
                dep.prepareGeometryChange()
                dep.update()
        return super().itemChange(change, value)

    def boundingRect(self) -> QRectF:
        r = self._radius + 2
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option, widget=None):
        selected = self.isSelected()
        color = QColor(0, 120, 215) if selected else self.color
        painter.setPen(QPen(color, 1.5))
        painter.setBrush(QBrush(color))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.drawEllipse(QPointF(0, 0), self._radius, self._radius)
