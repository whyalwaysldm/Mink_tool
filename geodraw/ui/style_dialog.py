"""
StyleDialog — dialog tùy chỉnh preset kích thước hiển thị.

Mỗi tab = 1 preset.  Mỗi tab có:
  • SpinBox cỡ điểm (point_radius)
  • SpinBox độ dày nét (stroke_width)
  • Widget xem trước trực tiếp
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QTabWidget, QWidget, QDoubleSpinBox, QLabel,
    QDialogButtonBox, QPushButton,
)
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF


# ── Widget xem trước ─────────────────────────────────────────────────────────

class _StylePreview(QWidget):
    """Vẽ 1 đoạn thẳng + 1 điểm ở giữa với radius / width hiện tại."""

    def __init__(self, point_radius: float, stroke_width: float, parent=None):
        super().__init__(parent)
        self._r = point_radius
        self._w = stroke_width
        self.setFixedSize(180, 54)
        self.setStyleSheet("background: white; border: 1px solid #ccc; border-radius: 4px;")

    def set_radius(self, r: float):
        self._r = r
        self.update()

    def set_width(self, w: float):
        self._w = w
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        # Nền trắng
        p.fillRect(self.rect(), QColor(255, 255, 255))

        # Đoạn thẳng
        pen = QPen(QColor(30, 30, 30), self._w)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(14, cy), QPointF(w - 14, cy))

        # Điểm ở giữa
        p.setPen(QPen(QColor(30, 30, 30), 1.2))
        p.setBrush(QBrush(QColor(30, 30, 30)))
        p.drawEllipse(QPointF(cx, cy), self._r, self._r)


# ── Dialog chính ──────────────────────────────────────────────────────────────

class StyleDialog(QDialog):
    """Cho phép người dùng chỉnh từng preset kích thước."""

    def __init__(self, style_manager, parent=None):
        super().__init__(parent)
        self._sm = style_manager
        self.setWindowTitle("Tùy chỉnh kích thước hiển thị")
        self.setMinimumWidth(340)
        self._widgets: dict = {}   # name → {"radius": spin, "width": spin, "preview": widget}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # ── Ghi chú ──────────────────────────────────────────────────────
        note = QLabel("Thay đổi sẽ áp dụng cho các điểm / đường vẽ <b>mới</b>.")
        note.setWordWrap(True)
        layout.addWidget(note)

        # ── Tab mỗi preset ───────────────────────────────────────────────
        tabs = QTabWidget()
        for name in self._sm.preset_names:
            preset  = self._sm.preset(name)
            tab     = QWidget()
            fl      = QFormLayout(tab)
            fl.setSpacing(10)
            fl.setContentsMargins(12, 12, 12, 12)

            # Cỡ điểm
            r_spin = QDoubleSpinBox()
            r_spin.setRange(1.0, 12.0)
            r_spin.setSingleStep(0.5)
            r_spin.setDecimals(1)
            r_spin.setSuffix(" px")
            r_spin.setValue(preset["point_radius"])
            fl.addRow("Cỡ điểm:", r_spin)

            # Độ dày nét
            w_spin = QDoubleSpinBox()
            w_spin.setRange(0.5, 10.0)
            w_spin.setSingleStep(0.2)
            w_spin.setDecimals(1)
            w_spin.setSuffix(" px")
            w_spin.setValue(preset["stroke_width"])
            fl.addRow("Độ dày nét:", w_spin)

            # Xem trước
            preview = _StylePreview(preset["point_radius"], preset["stroke_width"])
            fl.addRow("Xem trước:", preview)

            # Kết nối spin → preview (realtime)
            r_spin.valueChanged.connect(preview.set_radius)
            w_spin.valueChanged.connect(preview.set_width)

            self._widgets[name] = {
                "radius":  r_spin,
                "width":   w_spin,
                "preview": preview,
            }
            tabs.addTab(tab, name)

        layout.addWidget(tabs)

        # ── Nút bấm ──────────────────────────────────────────────────────
        btn_row = QHBoxLayout()

        restore_btn = QPushButton("Khôi phục mặc định")
        restore_btn.setToolTip("Đặt lại tất cả preset về giá trị ban đầu")
        restore_btn.clicked.connect(self._restore_defaults)
        btn_row.addWidget(restore_btn)
        btn_row.addStretch()

        std_btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        std_btns.accepted.connect(self._accept)
        std_btns.rejected.connect(self.reject)
        btn_row.addWidget(std_btns)

        layout.addLayout(btn_row)

    # ── Slots ─────────────────────────────────────────────────────────────

    def _accept(self):
        for name, w in self._widgets.items():
            self._sm.update_preset(name, w["radius"].value(), w["width"].value())
        self.accept()

    def _restore_defaults(self):
        defaults = self._sm.default_presets
        for name, w in self._widgets.items():
            if name in defaults:
                w["radius"].setValue(defaults[name]["point_radius"])
                w["width"].setValue(defaults[name]["stroke_width"])
