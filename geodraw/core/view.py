from PyQt6.QtWidgets import QGraphicsView, QGraphicsEllipseItem, QGraphicsItem
from PyQt6.QtGui import QTabletEvent, QWheelEvent, QPen, QBrush, QColor, QPainter
from PyQt6.QtCore import Qt, QPointF, QEvent, QRectF


# ── Snap indicator — hiệu ứng "nổi lên" kiểu GSP ────────────────────────────

class SnapIndicator(QGraphicsItem):
    """
    Vòng tròn nổi bật xuất hiện tại vị trí snap:
      • "point"        → vòng cam  (r=11) bao quanh điểm có sẵn
      • "intersection" → vòng xanh lá (r=8) + dấu × tại giao điểm
      • "on_curve"     → vòng xanh lam (r=7) + gạch ngang — điểm trên đường
    """

    _R = {"point": 11.0, "intersection": 8.0, "on_curve": 7.0}

    def __init__(self):
        super().__init__()
        self._snap_type = "free"
        self._r = 11.0
        self.setZValue(200)
        self.setVisible(False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, False)
        self.setAcceptedMouseButtons(Qt.MouseButton.NoButton)

    def update_snap(self, snap_result):
        """Gọi mỗi khi di chuột; snap_result là SnapResult từ scene.snap_info()."""
        if snap_result.snap_type == "free":
            self.setVisible(False)
            return
        self.prepareGeometryChange()
        self._snap_type = snap_result.snap_type
        self._r = self._R.get(snap_result.snap_type, 8.0)
        self.setPos(snap_result.pos)
        self.setVisible(True)
        self.update()

    def hide_snap(self):
        self.setVisible(False)

    # ── QGraphicsItem interface ───────────────────────────────────────────
    def boundingRect(self) -> QRectF:
        r = self._r + 4
        return QRectF(-r, -r, r * 2, r * 2)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self._snap_type == "point":
            # Vòng cam — bao quanh điểm có sẵn
            pen = QPen(QColor(255, 140, 0, 220), 2.2)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(255, 165, 0, 35)))
            painter.drawEllipse(QPointF(0, 0), self._r, self._r)

        elif self._snap_type == "intersection":
            # Vòng xanh lá + dấu ×
            pen = QPen(QColor(0, 190, 80, 230), 2.0)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 210, 80, 30)))
            painter.drawEllipse(QPointF(0, 0), self._r, self._r)
            s = self._r * 0.55
            painter.drawLine(QPointF(-s, -s), QPointF(s, s))
            painter.drawLine(QPointF(s, -s), QPointF(-s, s))

        elif self._snap_type == "on_curve":
            # Vòng xanh lam + gạch ngang (ký hiệu điểm trên đường)
            pen = QPen(QColor(0, 150, 230, 230), 2.0)
            painter.setPen(pen)
            painter.setBrush(QBrush(QColor(0, 170, 255, 28)))
            painter.drawEllipse(QPointF(0, 0), self._r, self._r)
            s = self._r * 0.6
            painter.drawLine(QPointF(-s, 0), QPointF(s, 0))   # gạch ngang


# ── Các tool không cần snap indicator ────────────────────────────────────────
_NO_SNAP_INDICATOR = {"ink", "erase", "select"}


class GeoView(QGraphicsView):

    def __init__(self, scene, tool_manager, parent=None):
        super().__init__(scene, parent)
        self._tm = tool_manager
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Vẽ lại toàn bộ khung nhìn mỗi lần thay đổi: các đường dài (đường thẳng,
        # tia) đổi hình theo điểm nên vẽ lại từng vùng nhỏ dễ để sót vệt cũ
        # (đường đã xóa vẫn hiện, cuộn trang thì hiện lại)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(
            QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WidgetAttribute.WA_TabletTracking, True)
        # Nền xám khớp với drawBackground của scene
        self.setBackgroundBrush(QBrush(QColor(115, 115, 115)))

        # ghost cursor: small circle showing hover position
        self._ghost = QGraphicsEllipseItem(-4, -4, 8, 8)
        self._ghost.setPen(QPen(QColor(0, 120, 215, 180), 1.5))
        self._ghost.setBrush(QBrush(QColor(0, 120, 215, 40)))
        self._ghost.setZValue(100)
        self._ghost.setVisible(False)
        scene.addItem(self._ghost)

        # snap indicator — nổi lên tại điểm snap / giao điểm
        self._snap_ind = SnapIndicator()
        scene.addItem(self._snap_ind)

    def _scene_pos(self, view_pos) -> QPointF:
        return self.mapToScene(view_pos)

    def _update_snap_indicator(self, scene_pos: QPointF):
        """Cập nhật vòng snap dựa theo vị trí con trỏ hiện tại."""
        tool_name = getattr(self._tm, 'current_name', '')
        if tool_name in _NO_SNAP_INDICATOR:
            self._snap_ind.hide_snap()
            return
        sc = self.scene()
        if hasattr(sc, 'snap_info'):
            result = sc.snap_info(scene_pos)
            self._snap_ind.update_snap(result)

    # ── Tablet events ───────────────────────────────────────────────────
    def tabletEvent(self, event: QTabletEvent):
        event.accept()
        scene_pos = self.mapToScene(event.position().toPoint())
        pressure = event.pressure()
        tool = self._tm.current_tool

        # update ghost cursor size by pressure
        w = max(4, pressure * 14)
        self._ghost.setRect(-w/2, -w/2, w, w)
        self._ghost.setPos(scene_pos)

        t = event.type()
        if t == QEvent.Type.TabletPress:
            self._ghost.setVisible(False)
            if tool:
                tool.tablet_press(scene_pos, pressure, event.button())
                # Bút không sinh double-click → tự nhận chạm đúp
                if self._is_pen_double_tap(event):
                    tool.double_click(scene_pos)
        elif t == QEvent.Type.TabletMove:
            if event.buttons() == Qt.MouseButton.NoButton:
                self._ghost.setVisible(True)
                self._update_snap_indicator(scene_pos)
                if tool:
                    tool.hover(scene_pos, pressure)
            else:
                self._ghost.setVisible(False)
                self._snap_ind.hide_snap()
                if tool:
                    tool.tablet_move(scene_pos, pressure)
        elif t == QEvent.Type.TabletRelease:
            self._ghost.setVisible(True)
            if tool:
                tool.tablet_release(scene_pos, pressure)

    def _is_pen_double_tap(self, event) -> bool:
        from PyQt6.QtCore import QElapsedTimer
        from PyQt6.QtWidgets import QApplication
        pos = event.position().toPoint()
        last = getattr(self, "_last_tap", None)
        is_double = (
            last is not None and
            last[0].elapsed() <= QApplication.doubleClickInterval() and
            (pos - last[1]).manhattanLength() <= 12
        )
        if is_double:
            self._last_tap = None
        else:
            timer = QElapsedTimer()
            timer.start()
            self._last_tap = (timer, pos)
        return is_double

    # ── Mouse events ────────────────────────────────────────────────────
    def mousePressEvent(self, event):
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        scene_pos = self.mapToScene(event.pos())
        self._ghost.setPos(scene_pos)
        if event.buttons() == Qt.MouseButton.NoButton:
            self._update_snap_indicator(scene_pos)
        else:
            self._snap_ind.hide_snap()
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def leaveEvent(self, event):
        self._snap_ind.hide_snap()
        self._ghost.setVisible(False)
        super().leaveEvent(event)

    # ── Zoom via Ctrl+scroll ─────────────────────────────────────────────
    def wheelEvent(self, event: QWheelEvent):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def zoom_in(self):
        self.scale(1.2, 1.2)

    def zoom_out(self):
        self.scale(1 / 1.2, 1 / 1.2)

    def set_zoom_percent(self, percent: int):
        """Đặt zoom cố định: 100 = 1 scene unit : 1 màn hình pixel.
        Sau đó cuộn để hiện góc trên-trái của trang 1."""
        self.resetTransform()
        factor = max(0.05, percent / 100.0)
        self.scale(factor, factor)
        sc = self.scene()
        if hasattr(sc, 'page_rect'):
            pr = sc.page_rect(0)
            # ensureVisible đảm bảo trang hiện ra với lề 30px mỗi phía
            self.ensureVisible(pr, 30, 30)

    def zoom_fit(self):
        from items.base import GeoItem
        geo_items = [it for it in self.scene().items()
                     if isinstance(it, GeoItem)]
        if geo_items:
            rect = self.scene().itemsBoundingRect()
            self.fitInView(rect.adjusted(-40, -40, 40, 40),
                           Qt.AspectRatioMode.KeepAspectRatio)
        else:
            # Không có hình → hiện trang đầu tiên với chút margin
            sc = self.scene()
            if hasattr(sc, 'page_rect'):
                pr = sc.page_rect(0)
                self.fitInView(pr.adjusted(-30, -30, 30, 30),
                               Qt.AspectRatioMode.KeepAspectRatio)
            else:
                self.fitInView(sc.sceneRect(),
                               Qt.AspectRatioMode.KeepAspectRatio)
