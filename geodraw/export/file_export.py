from PyQt6.QtWidgets import QGraphicsScene, QFileDialog, QWidget
from PyQt6.QtGui import QImage, QPainter, QPdfWriter, QPageSize
from PyQt6.QtSvg import QSvgGenerator
from PyQt6.QtCore import QRectF, Qt, QSize, QMarginsF
from pathlib import Path
from export.clipboard import _export_context, _visible_rect


def save_pdf(scene: QGraphicsScene, parent: QWidget = None,
             path: str = None) -> bool:
    """Xuất toàn bộ canvas thành PDF nhiều trang (mỗi trang giấy = 1 trang PDF)."""
    if path is None:
        path, _ = QFileDialog.getSaveFileName(
            parent, "Lưu PDF", "", "PDF (*.pdf)")
    if not path:
        return False

    writer = QPdfWriter(path)
    writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
    writer.setPageMargins(QMarginsF(0, 0, 0, 0))
    writer.setResolution(150)          # 150 DPI — cân bằng chất lượng / kích thước file

    painter = QPainter(writer)
    if not painter.isActive():
        return False
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Kích thước trang trên thiết bị (device pixels)
    pw = writer.width()
    ph = writer.height()
    target = QRectF(0, 0, pw, ph)

    page_count = scene.page_count() if hasattr(scene, 'page_count') else 1

    for i in range(page_count):
        if i > 0:
            writer.newPage()
        src = scene.page_rect(i) if hasattr(scene, 'page_rect') else scene.sceneRect()
        scene.render(painter, target=target, source=src)

    painter.end()
    return True


def save_png(scene: QGraphicsScene, parent: QWidget = None,
             path: str = None, dpi: int = 150) -> bool:
    if path is None:
        path, _ = QFileDialog.getSaveFileName(
            parent, "Lưu PNG", "", "PNG (*.png)")
    if not path:
        return False
    margin = 30
    with _export_context(scene):
        rect = _visible_rect(scene, margin)
        if rect.isNull() or rect.isEmpty():
            return False
        scale = dpi / 96.0
        w = int(rect.width() * scale)
        h = int(rect.height() * scale)
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(Qt.GlobalColor.white)
        painter = QPainter(img)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(scale, scale)
        scene.render(painter, source=rect)
        painter.end()
    return img.save(path, "PNG")


def save_svg(scene: QGraphicsScene, parent: QWidget = None,
             path: str = None) -> bool:
    if path is None:
        path, _ = QFileDialog.getSaveFileName(
            parent, "Lưu SVG", "", "SVG (*.svg)")
    if not path:
        return False
    margin = 30
    with _export_context(scene):
        rect = _visible_rect(scene, margin)
        if rect.isNull() or rect.isEmpty():
            return False
        gen = QSvgGenerator()
        gen.setFileName(path)
        gen.setSize(QSize(int(rect.width()), int(rect.height())))
        gen.setViewBox(QRectF(0, 0, rect.width(), rect.height()))
        painter = QPainter(gen)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        scene.render(painter, source=rect)
        painter.end()
    return True
