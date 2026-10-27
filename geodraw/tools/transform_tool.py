"""
Công cụ biến hình: đối xứng tâm, đối xứng trục, phép quay, phép vị tự.

Cách dùng:
  1. Đánh dấu (chuột phải — ở công cụ Chọn hoặc ngay trong công cụ biến hình):
     chuột phải vào điểm → "Đánh dấu tâm"; vào đoạn / đường thẳng / tia →
     "Đánh dấu trục"; vào chỗ trống → tạo điểm mới làm tâm.
     Tâm đã đánh dấu dùng chung cho đối xứng tâm, phép quay, vị tự.
  2. Bật công cụ, click đối tượng (điểm, đoạn, đường, đường tròn, đa giác,
     hình mẫu…) → tạo ảnh của nó. Click bên trong hình mẫu → cả hình.
  • Chọn sẵn nhiều đối tượng (công cụ Chọn) rồi bật công cụ: nếu đã có
    tâm / trục, cả nhóm được biến hình ngay; chưa có thì biến hình ngay
    sau khi đánh dấu.
"""
from PyQt6.QtCore import Qt, QPointF, QRectF
from PyQt6.QtGui import QPen, QBrush, QColor, QTransform
from PyQt6.QtWidgets import (QGraphicsItem, QGraphicsEllipseItem,
                             QGraphicsLineItem, QInputDialog)
from .base_tool import BaseTool
from items.point import PointItem
from items.segment import SegmentItem
from items.line import LineItem, RayItem
from items.transform import (Transform, transform_items, SUPPORTED_HINT,
                             POINT_REFLECT, AXIS_REFLECT, ROTATE, HOMOTHETY)

_LINE_TYPES = (SegmentItem, LineItem, RayItem)

def _marks_for(scene) -> dict:
    """Tâm / trục đánh dấu của một phiên (scene) — dùng chung giữa các công cụ biến hình."""
    if not hasattr(scene, "transform_marks"):
        scene.transform_marks = {"center": None, "axis": None}
    return scene.transform_marks


class _MarkOverlay:
    """Vòng / vạch màu cam hiển thị tâm hoặc trục đang được đánh dấu."""

    def __init__(self):
        self._ring = None
        self._line = None

    def show(self, scene, kind: str):
        self.hide()
        pen = QPen(QColor(230, 120, 0, 200), 2.5)
        pen.setCosmetic(True)
        if kind == AXIS_REFLECT and _marks_for(scene)["axis"] is not None:
            ax = _marks_for(scene)["axis"]
            a, b = ax.p1.scenePos(), ax.p2.scenePos()
            self._line = QGraphicsLineItem(a.x(), a.y(), b.x(), b.y())
            pen.setWidthF(5)
            pen.setColor(QColor(230, 120, 0, 110))
            self._line.setPen(pen)
            self._line.setZValue(60)
            scene.addItem(self._line)
        elif kind != AXIS_REFLECT and _marks_for(scene)["center"] is not None:
            c = _marks_for(scene)["center"].scenePos()
            self._ring = QGraphicsEllipseItem(-9, -9, 18, 18)
            self._ring.setPos(c)
            self._ring.setPen(pen)
            self._ring.setBrush(QBrush(QColor(230, 120, 0, 40)))
            self._ring.setZValue(60)
            scene.addItem(self._ring)

    def hide(self):
        for it in (self._ring, self._line):
            if it is not None and it.scene():
                it.scene().removeItem(it)
        self._ring = self._line = None


_overlay = _MarkOverlay()


def marked(scene, key: str):
    """Tâm ("center") / trục ("axis") đang đánh dấu, None nếu chưa có / đã xóa."""
    marks = _marks_for(scene)
    it = marks[key]
    if it is not None and it.scene() is None:
        marks[key] = None
    return marks[key]


def add_mark_actions(menu, scene, history, pos: QPointF, hits: list,
                     on_change=None):
    """
    Thêm vào menu chuột phải các mục đánh dấu tâm / trục cho phép biến hình.
    on_change(msg) được gọi sau khi đánh dấu thay đổi.
    """
    def set_mark(key, item, msg):
        _marks_for(scene)[key] = item
        if on_change:
            on_change(msg)

    def new_center():
        _, spos = scene.snap(pos)
        c = scene.new_point(spos)
        scene.addItem(c)
        history.push_add(scene, c)
        set_mark("center", c, "✓ Đã tạo điểm và đánh dấu làm tâm")

    snapped, _ = scene.snap(pos)
    pt = snapped if isinstance(snapped, PointItem) else \
        next((it for it in hits if isinstance(it, PointItem)), None)
    line = next((it for it in hits if isinstance(it, _LINE_TYPES)), None)
    if menu.actions():
        menu.addSeparator()
    if pt is not None:
        name = f" {pt.label}" if pt.label else ""
        menu.addAction(f"Đánh dấu tâm{name} (đối xứng tâm / quay / vị tự)") \
            .triggered.connect(lambda: set_mark(
                "center", pt, "✓ Đã đánh dấu tâm — dùng đối xứng tâm, "
                              "phép quay hoặc vị tự rồi click đối tượng"))
    if line is not None:
        menu.addAction("Đánh dấu trục đối xứng").triggered.connect(
            lambda: set_mark("axis", line, "✓ Đã đánh dấu trục — dùng đối xứng "
                                           "trục rồi click đối tượng"))
    if pt is None and line is None:
        menu.addAction("Tạo điểm tại đây làm tâm").triggered.connect(new_center)
    if marked(scene, "center") is not None:
        menu.addAction("Bỏ đánh dấu tâm").triggered.connect(
            lambda: set_mark("center", None, "Đã bỏ đánh dấu tâm"))
    if marked(scene, "axis") is not None:
        menu.addAction("Bỏ đánh dấu trục").triggered.connect(
            lambda: set_mark("axis", None, "Đã bỏ đánh dấu trục"))


class _TransformTool(BaseTool):
    kind = ""
    title = ""

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._pending: list = []      # đối tượng chọn sẵn, chờ có tâm / trục

    # ── Tham số (góc / tỉ số) ─────────────────────────────────────────
    def _ask_params(self) -> bool:
        return True

    def _transform(self) -> Transform:
        if self.kind == AXIS_REFLECT:
            ax = _marks_for(self.scene)["axis"]
            return Transform(AXIS_REFLECT, axis=(ax.p1, ax.p2))
        return Transform(self.kind, center=_marks_for(self.scene)["center"])

    def _marked(self):
        return marked(self.scene, "axis" if self.kind == AXIS_REFLECT else "center")

    # ── Lifecycle ─────────────────────────────────────────────────────
    def activate(self):
        self._pending = [it for it in self.scene.selectedItems()
                         if it is not self._marked()]
        if not self._ask_params():
            self._pending = []
        _overlay.show(self.scene, self.kind)
        if self._marked() is not None and self._pending:
            self._apply(self._pending)
            self._pending = []
        self._hint()

    def deactivate(self):
        _overlay.hide()
        self._pending = []

    def _hint(self):
        axis = self.kind == AXIS_REFLECT
        what = "đoạn / đường thẳng / tia → Đánh dấu trục" if axis \
            else "điểm → Đánh dấu tâm"
        if self._marked() is None:
            extra = f" — sẽ áp dụng cho {len(self._pending)} đối tượng đã chọn" \
                if self._pending else ""
            self.tm.status_hint.emit(
                f"{self.title}: chưa có {'trục' if axis else 'tâm'}"
                f" — chuột phải vào {what}{extra}")
        else:
            self.tm.status_hint.emit(
                f"{self.title}: click đối tượng để tạo ảnh ({SUPPORTED_HINT})"
                "  |  chuột phải để đổi tâm / trục")

    # ── Hit-test ──────────────────────────────────────────────────────
    def _items_at(self, pos: QPointF) -> list:
        view = self.scene.views()[0] if self.scene.views() else None
        tr = view.transform() if view else QTransform()
        return [it for it in self.scene.items(
                    pos, Qt.ItemSelectionMode.IntersectsItemShape,
                    Qt.SortOrder.DescendingOrder, tr)
                if hasattr(it, "color") and it.isVisible()
                and it.flags() & QGraphicsItem.GraphicsItemFlag.ItemIsSelectable]

    def _object_at(self, pos: QPointF):
        """Điểm (bắt dính) > đoạn / đường > đối tượng khác."""
        snapped, _ = self.scene.snap(pos)
        if isinstance(snapped, PointItem):
            return snapped
        hits = self._items_at(pos)
        for it in hits:
            if isinstance(it, _LINE_TYPES):
                return it
        from items.shape import ShapeItem
        for it in hits:
            if isinstance(it, ShapeItem):
                return it
        return hits[0] if hits else None

    # ── Events ────────────────────────────────────────────────────────
    def press(self, pos: QPointF, button, modifiers):
        if button == Qt.MouseButton.RightButton:
            self._context_menu(pos)
            return
        if button != Qt.MouseButton.LeftButton:
            return
        if self._marked() is None:
            self._hint()
            return
        obj = self._object_at(pos)
        if obj is not None and obj is self._marked():
            what = "trục" if self.kind == AXIS_REFLECT else "tâm"
            self.tm.status_hint.emit(
                f"{self.title}: đây là {what} đang đánh dấu — click đối tượng khác")
            return
        if obj is None:
            self.tm.status_hint.emit(
                f"{self.title}: hãy click vào một đối tượng ({SUPPORTED_HINT})")
            return
        from items.shape import shape_of
        shp = shape_of(obj)
        if shp is not None and obj is shp:
            obj = shp
        self._apply([obj])

    def _context_menu(self, pos: QPointF):
        from PyQt6.QtWidgets import QMenu
        from PyQt6.QtGui import QCursor
        view = self.scene.views()[0] if self.scene.views() else None
        menu = QMenu(view)
        add_mark_actions(menu, self.scene, self.history, pos, self._items_at(pos))
        if menu.exec(QCursor.pos()) is None:
            return
        _overlay.show(self.scene, self.kind)
        if self._marked() is not None and self._pending:
            self._apply(self._pending)
            self._pending = []
        self._hint()

    def _apply(self, objs: list):
        new_items = transform_items(self.scene, objs, self._transform())
        if not new_items:
            self.tm.status_hint.emit(f"{self.title}: đối tượng này chưa hỗ trợ")
            return
        for it in new_items:
            self.scene.addItem(it)
        self.history.push_add_batch(self.scene, new_items)
        self.scene.clearSelection()
        self.tm.status_hint.emit(
            f"✓ {self.title}: đã tạo ảnh của {len(objs)} đối tượng"
            "  —  click đối tượng khác")


class PointReflectTool(_TransformTool):
    name = "point_reflect"
    kind = POINT_REFLECT
    title = "Đối xứng tâm"


class AxisReflectTool(_TransformTool):
    name = "axis_reflect"
    kind = AXIS_REFLECT
    title = "Đối xứng trục"


class RotateTool(_TransformTool):
    name = "rotate"
    kind = ROTATE
    title = "Phép quay"
    angle = 90.0

    def _ask_params(self) -> bool:
        view = self.scene.views()[0] if self.scene.views() else None
        val, ok = QInputDialog.getDouble(
            view, "Phép quay",
            "Góc quay (độ, dương = ngược chiều kim đồng hồ):",
            RotateTool.angle, -360.0, 360.0, 1)
        if ok:
            RotateTool.angle = val
        return ok

    def _transform(self) -> Transform:
        return Transform(ROTATE, center=_marks_for(self.scene)["center"], angle=RotateTool.angle)


class HomothetyTool(_TransformTool):
    name = "homothety"
    kind = HOMOTHETY
    title = "Phép vị tự"
    ratio = 2.0

    def _ask_params(self) -> bool:
        view = self.scene.views()[0] if self.scene.views() else None
        val, ok = QInputDialog.getDouble(
            view, "Phép vị tự", "Tỉ số vị tự k (có thể âm):",
            HomothetyTool.ratio, -100.0, 100.0, 2)
        if ok and abs(val) > 1e-9:
            HomothetyTool.ratio = val
        return ok

    def _transform(self) -> Transform:
        return Transform(HOMOTHETY, center=_marks_for(self.scene)["center"], ratio=HomothetyTool.ratio)
