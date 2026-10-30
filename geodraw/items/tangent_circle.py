"""
Đường tròn tiếp xúc 2 đường thẳng và 1 đường tròn: CircleItem dựng từ
• TangentCenterItem — tâm (hiện ra), tự cập nhật khi các đường di chuyển;
• TangentRadiusPointItem — điểm ẩn trên đường tròn, cho biết bán kính.
Cả hai không kéo trực tiếp được.
"""
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QPointF
from .point import PointItem


class TangentCenterItem(PointItem):
    """Tâm đường tròn tiếp xúc; giữ nghiệm gần nghiệm cũ nhất khi hình thay đổi."""
    is_constrained = True

    def __init__(self, line1, line2, circle, center: QPointF, r: float,
                 anchors: list, color=None):
        self._updating = True         # cho phép đặt vị trí ban đầu = center
        self._hosts = (line1, line2, circle)
        self._anchors = list(anchors)
        self.r = r
        self.radius_pt = None
        super().__init__(center, color)
        self._updating = False
        for p in self._anchors:
            p.add_dependent(self)

    def _solve(self):
        from utils.snap_engine import curves_of
        from utils.tangent import tangent_circles
        curves = [curves_of(h) for h in self._hosts]
        if not all(curves):
            return None
        sols = tangent_circles(curves[0][0], curves[1][0], curves[2][0])
        if not sols:
            return None                # hiện không có nghiệm → giữ chỗ cũ
        cur = self.scenePos()
        return min(sols, key=lambda s: (s[0].x() - cur.x()) ** 2 +
                   (s[0].y() - cur.y()) ** 2 + (s[1] - self.r) ** 2)

    def update_position(self):
        sol = self._solve()
        if sol is None:
            return
        self.r = sol[1]
        self._updating = True
        self.setPos(sol[0])
        self._updating = False
        if self.radius_pt is not None:   # tâm đứng yên vẫn có thể đổi bán kính
            self.radius_pt.update_position()

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for p in self._anchors:
                p.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for p in self._anchors:
            p.remove_dependent(self)


class TangentRadiusPointItem(PointItem):
    """Điểm ẩn cách tâm đúng bằng bán kính hiện tại."""
    is_constrained = True

    def __init__(self, center: TangentCenterItem, color=None):
        self._updating = False
        self._center = center
        super().__init__(QPointF(0, 0), color)
        center.radius_pt = self
        center.add_dependent(self)
        self.setVisible(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.update_position()

    def update_position(self):
        c = self._center.scenePos()
        self._updating = True
        self.setPos(QPointF(c.x() + self._center.r, c.y()))
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        return super().itemChange(change, value)

    def remove_from_scene(self):
        self._center.remove_dependent(self)
