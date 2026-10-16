from contextlib import contextmanager
from PyQt6.QtWidgets import QApplication, QGraphicsScene
from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtCore import QRectF, Qt


@contextmanager
def _export_context(scene: QGraphicsScene):
    """
    Context manager: tạm thời ẩn hoàn toàn (opacity=0) các item có _is_hidden=True,
    rồi phục hồi sau khi render xong.
    """
    from items.base import GeoItem
    hidden_items = [it for it in scene.items()
                    if isinstance(it, GeoItem) and getattr(it, '_is_hidden', False)]
    for it in hidden_items:
        it.setOpacity(0.0)
    try:
        yield
    finally:
        for it in hidden_items:
            it.setOpacity(GeoItem.HIDDEN_OPACITY)


def _visible_rect(scene: QGraphicsScene, margin: int = 30) -> QRectF:
    """Bounding rect chỉ của các item không bị ẩn."""
    from items.base import GeoItem
    rect = QRectF()
    for item in scene.items():
        if isinstance(item, GeoItem) and getattr(item, '_is_hidden', False):
            continue
        br = item.sceneBoundingRect()
        if rect.isNull():
            rect = br
        else:
            rect = rect.united(br)
    if rect.isNull():
        return rect
    return rect.adjusted(-margin, -margin, margin, margin)


def render_to_clipboard(scene: QGraphicsScene, margin: int = 30,
                         bg_color=None) -> bool:
    with _export_context(scene):
        rect = _visible_rect(scene, margin)
        if rect.isNull() or rect.isEmpty():
            return False
        img = QImage(int(rect.width()), int(rect.height()),
                     QImage.Format.Format_ARGB32)
        img.fill(bg_color or Qt.GlobalColor.white)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, source=rect)
        painter.end()
    QApplication.clipboard().setImage(img)
    return True
