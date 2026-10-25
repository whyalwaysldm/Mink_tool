"""
Phép biến hình: đối xứng tâm, đối xứng trục, phép quay, phép vị tự.

• TransformedPointItem — ảnh của một điểm qua phép biến hình. Tự cập nhật
  khi điểm gốc, tâm hoặc trục di chuyển; không kéo trực tiếp được.
• transform_items()    — tạo ảnh của một nhóm đối tượng (điểm, đoạn, đường,
  tia, đường tròn, cung, đa giác, hình mẫu…), dùng chung ảnh cho điểm chung.
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtCore import QPointF
from .point import PointItem

POINT_REFLECT = "point_reflect"     # đối xứng tâm
AXIS_REFLECT  = "axis_reflect"      # đối xứng trục
ROTATE        = "rotate"            # phép quay (góc độ, dương = ngược chiều kim đồng hồ)
HOMOTHETY     = "homothety"         # phép vị tự (tỉ số k)


class Transform:
    """Mô tả phép biến hình. Tâm / trục là PointItem để ảnh tự cập nhật."""

    def __init__(self, kind: str, center: PointItem = None, axis: tuple = None,
                 angle: float = 0.0, ratio: float = 1.0):
        self.kind = kind
        self.center = center
        self.axis = axis            # (p1, p2) của đường làm trục
        self.angle = angle
        self.ratio = ratio

    def anchors(self) -> list:
        return list(self.axis) if self.kind == AXIS_REFLECT else [self.center]

    def apply(self, p: QPointF) -> QPointF:
        if self.kind == AXIS_REFLECT:
            a, b = self.axis[0].scenePos(), self.axis[1].scenePos()
            dx, dy = b.x() - a.x(), b.y() - a.y()
            L2 = dx * dx + dy * dy or 1.0
            t = ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / L2
            fx, fy = a.x() + dx * t, a.y() + dy * t
            return QPointF(2 * fx - p.x(), 2 * fy - p.y())
        c = self.center.scenePos()
        vx, vy = p.x() - c.x(), p.y() - c.y()
        if self.kind == POINT_REFLECT:
            return QPointF(c.x() - vx, c.y() - vy)
        if self.kind == ROTATE:
            # Trục y màn hình hướng xuống → đổi dấu để góc dương là ngược chiều kim đồng hồ
            t = math.radians(-self.angle)
            cs, sn = math.cos(t), math.sin(t)
            return QPointF(c.x() + vx * cs - vy * sn, c.y() + vx * sn + vy * cs)
        if self.kind == HOMOTHETY:
            return QPointF(c.x() + vx * self.ratio, c.y() + vy * self.ratio)
        return QPointF(p)


class TransformedPointItem(PointItem):
    """Ảnh của điểm src qua phép biến hình T."""
    is_constrained = True

    def __init__(self, src: PointItem, T: Transform, color=None):
        self._updating = False
        self._src, self._T = src, T
        super().__init__(QPointF(0, 0), color)
        for p in self._deps():
            p.add_dependent(self)
        self.update_position()

    def _deps(self) -> list:
        return [self._src] + self._T.anchors()

    def update_position(self):
        self._updating = True
        self.setPos(self._T.apply(self._src.scenePos()))
        self._updating = False

    def itemChange(self, change, value):
        if (change == QGraphicsItem.GraphicsItemChange.ItemPositionChange
                and not self._updating):
            return self.pos()
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged \
                and self.scene() is not None:
            for p in self._deps():
                p.add_dependent(self)     # khôi phục sau undo xóa
        return super().itemChange(change, value)

    def remove_from_scene(self):
        for p in self._deps():
            p.remove_dependent(self)


def _prime_name(name: str, used: set) -> str:
    n = name + "'"
    while n in used:
        n += "'"
    return n


def transform_items(scene, items: list, T: Transform) -> list:
    """Tạo ảnh của các đối tượng qua T. Trả về danh sách item mới (chưa thêm vào scene)."""
    from .segment import SegmentItem
    from .line import LineItem, RayItem
    from .circle import CircleItem
    from .arc import ArcItem
    from .polygon import PolygonItem
    from .shape import ShapeItem
    from .circumcircle import CircumcircleItem
    from .bisector_ray import BisectorRayItem
    from .point_label import PointLabelItem

    images: dict = {}
    new_items: list = []
    used_names = {p.label for p in scene.items()
                  if isinstance(p, PointItem) and getattr(p, "label", "")}

    def img(p: PointItem) -> PointItem:
        if p in images:
            return images[p]
        q = TransformedPointItem(p, T)
        if not p.isVisible():                 # điểm ẩn (điểm phụ của đường / đường tròn)
            q.setVisible(False)
            q.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        images[p] = q
        new_items.append(q)
        if p.isVisible() and getattr(p, "label", ""):
            name = _prime_name(p.label, used_names)
            used_names.add(name)
            q.label = name
            new_items.append(PointLabelItem(q, name))
        return q

    # Hình mẫu được chọn cả hình → kèm các cạnh của nó
    expanded = []
    for it in items:
        expanded.append(it)
        if isinstance(it, ShapeItem):
            expanded.extend(e for e in it.edges if e not in items)

    # Đường tròn ngoại tiếp đã kèm tâm (CircumcenterItem) → bỏ qua tâm riêng
    for it in expanded:
        if isinstance(it, PointItem):
            img(it)
        elif isinstance(it, RayItem):
            new_items.append(RayItem(img(it.p1), img(it.p2)))
        elif isinstance(it, LineItem):
            new_items.append(LineItem(img(it.p1), img(it.p2)))
        elif isinstance(it, SegmentItem):
            new_items.append(SegmentItem(img(it.p1), img(it.p2)))
        elif isinstance(it, CircleItem):
            new_items.append(CircleItem(img(it.center_pt), img(it.radius_pt)))
        elif isinstance(it, ArcItem):
            new_items.append(ArcItem(img(it.p_start), img(it.p_mid), img(it.p_end)))
        elif isinstance(it, CircumcircleItem):
            new_items.append(CircumcircleItem(img(it._p1), img(it._p2), img(it._p3)))
        elif isinstance(it, BisectorRayItem):
            new_items.append(BisectorRayItem(img(it._p1), img(it._vertex), img(it._p2)))
        elif isinstance(it, ShapeItem):
            new_items.append(PolygonItem([img(p) for p in it.points]))
        elif isinstance(it, PolygonItem):
            new_items.append(PolygonItem([img(p) for p in it.points],
                                         closed=it.closed))
            # kèm các cạnh là đoạn thẳng nối 2 đỉnh liên tiếp
            pts = it.points
            n = len(pts)
            pairs = {(pts[k], pts[(k + 1) % n]) for k in range(n)}
            for s in scene.items():
                if isinstance(s, SegmentItem) and s not in expanded and \
                        ((s.p1, s.p2) in pairs or (s.p2, s.p1) in pairs):
                    new_items.append(SegmentItem(img(s.p1), img(s.p2)))
    return new_items


SUPPORTED_HINT = "điểm, đoạn, đường thẳng, tia, đường tròn, cung, đa giác, hình mẫu"
