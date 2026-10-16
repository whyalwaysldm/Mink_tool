from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QPointF
from .point import PointItem


class MidpointItem(PointItem):
    """Point constrained to midpoint of two parent PointItems."""
    is_constrained = True

    def __init__(self, p1: PointItem, p2: PointItem, color=None):
        self._updating = False
        self._p1 = p1
        self._p2 = p2
        super().__init__(QPointF(0, 0), color)
        p1.add_dependent(self)
        p2.add_dependent(self)
        self.update_position()

    def _compute_pos(self) -> QPointF:
        a = self._p1.scenePos()
        b = self._p2.scenePos()
        return QPointF((a.x() + b.x()) / 2, (a.y() + b.y()) / 2)

    def update_position(self):
        self._updating = True
        self.setPos(self._compute_pos())
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        return super().itemChange(change, value)

    def remove_from_scene(self):
        self._p1.remove_dependent(self)
        self._p2.remove_dependent(self)
