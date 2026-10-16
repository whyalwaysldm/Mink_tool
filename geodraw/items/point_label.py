"""
PointLabelItem — nhãn chữ gắn với một PointItem.

• Hiển thị tên điểm bằng font toán (Times New Roman italic).
• Có thể kéo bằng SelectTool nhưng bị giữ trong vòng MAX_DIST px quanh điểm.
• Khi điểm di chuyển, nhãn theo cùng (giữ nguyên offset).
• Kéo điểm + nhãn cùng lúc → nhãn không bị constraint (offset giữ nguyên).
"""
import math
from PyQt6.QtWidgets import QGraphicsItem
from PyQt6.QtGui import (QPainter, QPen, QBrush, QColor,
                          QFont, QFontMetricsF)
from PyQt6.QtCore import QRectF, QPointF, Qt
from .base import GeoItem
from .point import PointItem

MAX_DIST = 52.0   # px — xa nhất nhãn có thể cách tâm điểm
MIN_DIST =  7.0   # px — gần nhất (tránh đè lên dot điểm)


class PointLabelItem(GeoItem):

    def __init__(self, point: PointItem, text: str,
                 offset: QPointF = None):
        super().__init__()
        self._point = point
        self._text  = text
        # offset: vector từ scenePos(point) → scenePos(label-baseline-left)
        self._offset = QPointF(offset) if offset else QPointF(9, -11)
        self._moving_by_point = False   # guard: programmatic move

        # Không dùng ItemIsMovable vì SelectTool dùng setPos() trực tiếp.
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable,         True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable,            False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setZValue(15)

        point.add_dependent(self)
        self._sync_pos()

    # ── Text property ─────────────────────────────────────────────────────

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str):
        self.prepareGeometryChange()
        self._text = value
        self._point.label = value    # keep point.label in sync
        self.update()

    # ── Sync với điểm cha ────────────────────────────────────────────────

    def _sync_pos(self):
        """Đặt vị trí theo điểm + offset đã lưu (không kích hoạt clamp)."""
        self._moving_by_point = True
        self.setPos(self._point.scenePos() + self._offset)
        self._moving_by_point = False

    def update_position(self):
        """Gọi bởi PointItem.itemChange khi điểm di chuyển."""
        if self.isSelected():
            # SelectTool đang kéo nhãn trực tiếp — bỏ qua để tránh double-move
            return
        self._sync_pos()

    # ── Khi xóa khỏi scene ───────────────────────────────────────────────

    def remove_from_scene(self):
        self._point.remove_dependent(self)
        self._point.label = ""
        if getattr(self._point, '_label_item', None) is self:
            self._point._label_item = None

    # ── itemChange: clamp + khôi phục khi undo/redo ──────────────────────

    def itemChange(self, change, value):
        GIC = QGraphicsItem.GraphicsItemChange

        # ── Khi được thêm vào scene (kể cả undo/redo) ──────────────────
        if change == GIC.ItemSceneHasChanged:
            sc = self.scene()
            if sc is not None:
                # Khôi phục dependency nếu bị mất (ví dụ sau undo remove)
                if self not in self._point._dependents:
                    self._point.add_dependent(self)
                self._point.label = self._text
                self._point._label_item = self
            return value

        # ── Clamp khi người dùng kéo (không phải point kéo nhãn đi) ────
        if change == GIC.ItemPositionChange:
            if self._moving_by_point or self._point.isSelected():
                # Kéo đa-item hoặc programmatic → không constraint
                return value
            # Kéo nhãn một mình: giữ trong [MIN_DIST, MAX_DIST]
            pt  = self._point.scenePos()
            dx  = value.x() - pt.x()
            dy  = value.y() - pt.y()
            d   = math.sqrt(dx * dx + dy * dy)
            if d < 1e-9:
                return value
            if d > MAX_DIST:
                s  = MAX_DIST / d
                dx *= s; dy *= s
            elif d < MIN_DIST:
                s  = MIN_DIST / d
                dx *= s; dy *= s
            return QPointF(pt.x() + dx, pt.y() + dy)

        # ── Sau khi kéo nhãn xong: cập nhật offset đã lưu ──────────────
        if change == GIC.ItemPositionHasChanged:
            if not self._moving_by_point and not self._point.isSelected():
                pt = self._point.scenePos()
                self._offset = QPointF(
                    self.scenePos().x() - pt.x(),
                    self.scenePos().y() - pt.y(),
                )
            return value

        return super().itemChange(change, value)

    # ── Vẽ ───────────────────────────────────────────────────────────────

    @staticmethod
    def _font() -> QFont:
        f = QFont("Times New Roman", 13)
        f.setItalic(True)
        return f

    def boundingRect(self) -> QRectF:
        if not self._text:
            return QRectF(-2, -2, 4, 4)
        fm  = QFontMetricsF(self._font())
        w   = fm.horizontalAdvance(self._text)
        asc = fm.ascent()
        des = fm.descent()
        pad = 3
        return QRectF(-pad, -(asc + pad), w + pad * 2, asc + des + pad * 2)

    def paint(self, painter: QPainter, option, widget=None):
        if not self._text:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        if selected:
            painter.fillRect(
                self.boundingRect(),
                QColor(0, 120, 215, 28))
        color = QColor(0, 90, 200) if selected else QColor(20, 20, 20)
        painter.setFont(self._font())
        painter.setPen(QPen(color, 1.0))
        # drawText với baseline tại (0, 0)
        painter.drawText(QPointF(0, 0), self._text)
