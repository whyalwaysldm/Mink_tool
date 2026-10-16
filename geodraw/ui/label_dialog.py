"""Hộp thoại nhập nội dung nhãn + chọn font và cỡ chữ."""
from PyQt6.QtWidgets import (QDialog, QFormLayout, QLineEdit, QFontComboBox,
                              QSpinBox, QLabel, QDialogButtonBox, QVBoxLayout)
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt

from items.label import MIN_FONT_SIZE, MAX_FONT_SIZE


class LabelDialog(QDialog):

    def __init__(self, parent=None, title="Nhãn", text="",
                 family="Times New Roman", size=12, italic=False,
                 show_text=True):
        super().__init__(parent)
        self.setWindowTitle(title)
        self._italic = italic

        self._text = QLineEdit(text)
        self._text.setVisible(show_text)
        self._family = QFontComboBox()
        self._family.setCurrentFont(QFont(family))
        self._size = QSpinBox()
        self._size.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self._size.setValue(int(size))
        self._size.setSuffix(" pt")
        self._preview = QLabel()
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setMinimumHeight(60)

        form = QFormLayout()
        if show_text:
            form.addRow("Nội dung:", self._text)
        form.addRow("Font chữ:", self._family)
        form.addRow("Cỡ chữ:", self._size)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(self._preview)
        lay.addWidget(buttons)

        self._text.textChanged.connect(self._update_preview)
        self._family.currentFontChanged.connect(self._update_preview)
        self._size.valueChanged.connect(self._update_preview)
        self._update_preview()
        self._text.setFocus()
        self._text.selectAll()

    def _update_preview(self, *_):
        f = QFont(self._family.currentFont().family(), self._size.value())
        f.setItalic(self._italic)
        self._preview.setFont(f)
        self._preview.setText(self._text.text() or "AaBb 123")

    def values(self) -> tuple:
        """(text, family, size)"""
        return (self._text.text().strip(),
                self._family.currentFont().family(),
                self._size.value())


def _view_of(scene):
    views = scene.views()
    return views[0] if views else None


def remember_label_font(family: str, size: int):
    """Lưu font/cỡ chữ vừa dùng làm mặc định cho nhãn mới."""
    from config.app_settings import AppSettings
    s = AppSettings.load()
    if (s.label_font_family, s.label_font_size) != (family, size):
        s.label_font_family = family
        s.label_font_size = size
        s.save()


def edit_label(item, scene, history) -> bool:
    """Mở hộp thoại sửa nhãn (LabelItem hoặc PointLabelItem). True nếu đã đổi."""
    from items.label import LabelItem
    old = item.style_state()
    text, family, size = old
    dlg = LabelDialog(_view_of(scene), "Sửa nhãn", text, family, size,
                      italic=not isinstance(item, LabelItem))
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False
    new_text, new_family, new_size = dlg.values()
    if not new_text:
        new_text = text   # không cho xóa trắng nội dung ở đây
    new = (new_text, new_family, new_size)
    history.push_label_style(item, old, new)
    if isinstance(item, LabelItem):
        remember_label_font(new_family, new_size)
    return old != new


def resize_labels(items, step: int, history) -> int:
    """Tăng / giảm cỡ chữ các nhãn đang chọn. Trả về số nhãn đã đổi."""
    labels = [it for it in items if hasattr(it, "apply_style_state")]
    if not labels:
        return 0
    history.stack.beginMacro("Resize labels")
    for it in labels:
        old = it.style_state()
        size = max(MIN_FONT_SIZE, min(MAX_FONT_SIZE, old[2] + step))
        history.push_label_style(it, old, (old[0], old[1], size))
    history.stack.endMacro()
    return len(labels)
