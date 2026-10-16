from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QRadioButton, QSpinBox, QLabel, QDialogButtonBox,
    QSizePolicy,
)
from PyQt6.QtCore import Qt
from config.app_settings import AppSettings


class SettingsDialog(QDialog):
    """Hộp thoại cài đặt ứng dụng."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Cài đặt — GeoDraw")
        self.setFixedSize(400, 200)
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        settings = AppSettings.load()

        root = QVBoxLayout(self)
        root.setSpacing(12)

        # ── Group: Zoom khởi động ─────────────────────────────────────────
        grp = QGroupBox("Zoom trang giấy khi khởi động chương trình")
        gl  = QVBoxLayout(grp)
        gl.setSpacing(8)

        # Lựa chọn 1: vừa trang tự động
        self._rb_fit = QRadioButton("Vừa trang tự động  (khuyến nghị)")

        # Lựa chọn 2: cố định %
        row = QHBoxLayout()
        self._rb_pct = QRadioButton("Cố định:")
        self._spin   = QSpinBox()
        self._spin.setRange(25, 300)
        self._spin.setSingleStep(5)
        self._spin.setSuffix("  %")
        self._spin.setFixedWidth(90)
        self._spin.setAlignment(Qt.AlignmentFlag.AlignRight)

        lbl_hint = QLabel("<small><i>  (25 % – 300 %)</i></small>")
        lbl_hint.setSizePolicy(QSizePolicy.Policy.Expanding,
                               QSizePolicy.Policy.Preferred)

        row.addWidget(self._rb_pct)
        row.addWidget(self._spin)
        row.addWidget(lbl_hint)
        row.addStretch()

        gl.addWidget(self._rb_fit)
        gl.addLayout(row)
        root.addWidget(grp)

        # ── Khởi tạo giá trị ─────────────────────────────────────────────
        pct = settings.initial_zoom_percent
        if pct > 0:
            self._rb_pct.setChecked(True)
            self._spin.setValue(pct)
        else:
            self._rb_fit.setChecked(True)
            self._spin.setValue(75)       # giá trị gợi ý mặc định
            self._spin.setEnabled(False)

        # Bật/tắt spinbox theo radio
        self._rb_fit.toggled.connect(
            lambda checked: self._spin.setEnabled(not checked))

        # ── OK / Cancel ───────────────────────────────────────────────────
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Ok).setText("Lưu")
        btns.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        btns.accepted.connect(self._save_and_accept)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ── Lưu và đóng ──────────────────────────────────────────────────────
    def _save_and_accept(self):
        s = AppSettings.load()
        s.initial_zoom_percent = (
            self._spin.value() if self._rb_pct.isChecked() else 0)
        s.save()
        self.accept()
