from PyQt6.QtWidgets import QGraphicsScene, QGraphicsRectItem, QGraphicsItem
from PyQt6.QtCore import QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPen, QBrush, QFont

from items.point import PointItem


# ── Kích thước trang A4 @ 96 dpi (~210 × 297 mm) ────────────────────────────
PAGE_W   = 794
PAGE_H   = 1123
PAGE_GAP = 40     # khoảng cách giữa các trang & viền trên/dưới
MARGIN_X = 90     # viền xám hai bên


def _page_rect(index: int) -> QRectF:
    """Toạ độ scene của trang thứ index (0-based)."""
    return QRectF(-PAGE_W / 2,
                  PAGE_GAP + index * (PAGE_H + PAGE_GAP),
                  PAGE_W, PAGE_H)


def _scene_rect(page_count: int) -> QRectF:
    total_h = page_count * (PAGE_H + PAGE_GAP) + PAGE_GAP
    w = PAGE_W + 2 * MARGIN_X
    return QRectF(-w / 2, 0, w, total_h)


# ── Item trang giấy (không interactive) ─────────────────────────────────────

class _PageShadow(QGraphicsRectItem):
    IS_PAGE_DECO = True
    def __init__(self, pr):
        super().__init__(pr.translated(4, 5))
        self.setPen(QPen(Qt.PenStyle.NoPen))
        self.setBrush(QBrush(QColor(0, 0, 0, 55)))
        self.setZValue(-20)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)


class _PageRect(QGraphicsRectItem):
    IS_PAGE_DECO = True
    def __init__(self, pr):
        super().__init__(pr)
        self.setPen(QPen(QColor(180, 180, 180), 0.8))
        self.setBrush(QBrush(QColor(255, 255, 255)))
        self.setZValue(-10)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)


# ── Scene chính ──────────────────────────────────────────────────────────────

class GeoScene(QGraphicsScene):

    def __init__(self, history, parent=None):
        super().__init__(parent)
        self.history = history
        self._tool   = None

        self._page_count     = 0
        self._expand_pending = False

        # Khởi tạo trang đầu tiên
        self._add_page()

        # Theo dõi thay đổi item (ink stroke lớn dần, drag…)
        self.changed.connect(self._on_scene_changed)

    # ── Page API ──────────────────────────────────────────────────────────

    def page_rect(self, index: int) -> QRectF:
        return _page_rect(index)

    def page_count(self) -> int:
        return self._page_count

    def _last_page_bottom(self) -> float:
        return _page_rect(self._page_count - 1).bottom()

    def _add_page(self):
        """Thêm trang kế tiếp (tăng _page_count và thêm item trang)."""
        idx = self._page_count
        self._page_count += 1
        self.setSceneRect(_scene_rect(self._page_count))

        pr = _page_rect(idx)
        # Dùng QGraphicsScene.addItem gốc để tránh trigger check lại
        QGraphicsScene.addItem(self, _PageShadow(pr))
        QGraphicsScene.addItem(self, _PageRect(pr))

    # ── Tự động thêm trang ────────────────────────────────────────────────

    def _on_scene_changed(self, _regions):
        self._schedule_expand()

    def _schedule_expand(self):
        if not self._expand_pending:
            self._expand_pending = True
            QTimer.singleShot(0, self._check_expand)

    def _check_expand(self):
        self._expand_pending = False
        from items.base import GeoItem

        threshold = self._last_page_bottom()   # chính xác tại đáy trang cuối

        for item in self.items():
            if not isinstance(item, GeoItem):
                continue
            if item.sceneBoundingRect().bottom() > threshold:
                self._add_page()
                # Kiểm tra tiếp nếu cần nhiều trang hơn
                self._schedule_expand()
                return

    # ── Override addItem: chỉ trigger expand cho GeoItem ─────────────────

    def addItem(self, item):
        super().addItem(item)
        from items.base import GeoItem
        if isinstance(item, GeoItem):
            self._schedule_expand()

    # ── Nền xám (bàn làm việc) + số trang ────────────────────────────────

    def drawBackground(self, painter, rect):
        # Nền xám
        painter.fillRect(rect, QColor(115, 115, 115))

        # Số trang hiện dưới mỗi trang (chỉ khi > 1 trang)
        if self._page_count <= 1:
            return
        font = QFont("Arial", 9)
        font.setItalic(True)
        painter.setFont(font)
        painter.setPen(QColor(200, 200, 200))
        for i in range(self._page_count):
            pr = _page_rect(i)
            lbl = QRectF(pr.left(), pr.bottom() + 5,
                         pr.width(), PAGE_GAP - 10)
            if rect.intersects(lbl):
                painter.drawText(
                    lbl,
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
                    f"— Trang {i + 1} —",
                )

    # ── Snap & tools ──────────────────────────────────────────────────────

    def set_tool(self, tool):
        self._tool = tool

    def point_items(self) -> list:
        return [it for it in self.items() if isinstance(it, PointItem)]

    def snap(self, pos, exclude=None):
        """Backward-compat: trả về (item_or_None, snapped_pos)."""
        from utils.snap_engine import snap as _snap
        r = _snap(pos, self, exclude)
        return r.item, r.pos

    def snap_info(self, pos, exclude=None):
        """Trả về SnapResult (item, pos, snap_type) — dùng cho view indicator."""
        from utils.snap_engine import snap as _snap
        return _snap(pos, self, exclude)

    # ── Mouse events → active tool ────────────────────────────────────────

    def mousePressEvent(self, event):
        if self._tool:
            self._tool.press(event.scenePos(), event.button(), event.modifiers())
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._tool:
            self._tool.move(event.scenePos(), event.modifiers())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._tool:
            self._tool.release(event.scenePos(), event.button())
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self._tool:
            self._tool.double_click(event.scenePos())
        else:
            super().mouseDoubleClickEvent(event)
