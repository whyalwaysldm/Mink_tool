from PyQt6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QSlider, QColorDialog,
                              QDoubleSpinBox, QSpinBox, QFontComboBox)
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt
from items.base import GeoItem
from items.ink_stroke import InkStrokeItem


class PropertiesPanel(QDockWidget):

    def __init__(self, scene, tool_manager, parent=None):
        super().__init__("Thuộc tính", parent)
        self._scene = scene
        self._tm = tool_manager
        self.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable |
                         QDockWidget.DockWidgetFeature.DockWidgetFloatable)

        w = QWidget()
        self.setWidget(w)
        lay = QVBoxLayout(w)
        lay.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Color button
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Màu:"))
        self._color_btn = QPushButton()
        self._color_btn.setFixedSize(32, 22)
        self._color_btn.clicked.connect(self._pick_color)
        self._set_btn_color(QColor(30, 30, 30))
        h1.addWidget(self._color_btn)
        h1.addStretch()
        lay.addLayout(h1)

        # Stroke width
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Độ dày:"))
        self._width_spin = QDoubleSpinBox()
        self._width_spin.setRange(0.5, 10.0)
        self._width_spin.setSingleStep(0.5)
        self._width_spin.setValue(1.8)
        self._width_spin.valueChanged.connect(self._apply_width)
        h2.addWidget(self._width_spin)
        lay.addLayout(h2)

        # Ink width
        h3 = QHBoxLayout()
        h3.addWidget(QLabel("Bút vẽ:"))
        self._ink_spin = QDoubleSpinBox()
        self._ink_spin.setRange(1.0, 20.0)
        self._ink_spin.setSingleStep(0.5)
        self._ink_spin.setValue(3.0)
        self._ink_spin.valueChanged.connect(self._apply_ink_width)
        h3.addWidget(self._ink_spin)
        lay.addLayout(h3)

        # ── Chữ của nhãn: font + cỡ chữ ───────────────────────────────
        # Áp dụng cho nhãn đang chọn; không chọn gì → mặc định cho nhãn mới
        self.addSeparator_()
        from config.app_settings import AppSettings
        from items.label import MIN_FONT_SIZE, MAX_FONT_SIZE
        _s = AppSettings.load()
        self._updating_font = False
        lay.addWidget(QLabel("Chữ (nhãn):"))
        self._font_combo = QFontComboBox()
        self._font_combo.setCurrentFont(QFont(_s.label_font_family))
        self._font_combo.setToolTip(
            "Font của nhãn đang chọn\n(không chọn nhãn nào → font cho nhãn mới)")
        self._font_combo.currentFontChanged.connect(self._apply_label_font)
        lay.addWidget(self._font_combo)
        h_fs = QHBoxLayout()
        h_fs.addWidget(QLabel("Cỡ chữ:"))
        self._font_size_spin = QSpinBox()
        self._font_size_spin.setRange(MIN_FONT_SIZE, MAX_FONT_SIZE)
        self._font_size_spin.setValue(_s.label_font_size)
        self._font_size_spin.setSuffix(" pt")
        self._font_size_spin.setToolTip(
            "Cỡ chữ của nhãn đang chọn (phím tắt: + / −)\n"
            "(không chọn nhãn nào → cỡ chữ cho nhãn mới)")
        self._font_size_spin.valueChanged.connect(self._apply_label_font)
        h_fs.addWidget(self._font_size_spin)
        lay.addLayout(h_fs)

        # ── Ẩn / Hiện ──────────────────────────────────────────────────
        self.addSeparator_()
        h_vis = QHBoxLayout()
        self._hide_btn = QPushButton("👁  Ẩn")
        self._hide_btn.setToolTip(
            "Ẩn/Hiện đối tượng được chọn (phím tắt: H)\n"
            "H không chọn gì → hiện tất cả đối tượng ẩn")
        self._hide_btn.setCheckable(True)
        f = QFont()
        f.setPointSize(9)
        self._hide_btn.setFont(f)
        self._hide_btn.clicked.connect(self._on_hide_btn)
        h_vis.addWidget(self._hide_btn)
        lay.addLayout(h_vis)

        scene.selectionChanged.connect(self._on_selection)

    def addSeparator_(self):
        """Thêm đường kẻ ngang ngăn cách các nhóm thuộc tính."""
        from PyQt6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        self.widget().layout().addWidget(line)

    def _set_btn_color(self, color: QColor):
        self._current_color = color
        self._color_btn.setStyleSheet(
            f"background-color: {color.name()}; border: 1px solid #888;")

    def _pick_color(self):
        color = QColorDialog.getColor(self._current_color, self.widget())
        if color.isValid():
            self._set_btn_color(color)
            self._apply_color(color)

    def _apply_color(self, color: QColor):
        for it in self._scene.selectedItems():
            if isinstance(it, GeoItem):
                it.color = QColor(color)
                if hasattr(it, "_text_item"):        # LabelItem
                    it._text_item.setDefaultTextColor(QColor(color))
                it.update()
        ink = self._tm.all_tools().get("ink")
        if ink:
            ink.ink_color = QColor(color)

    def _apply_width(self, val: float):
        for it in self._scene.selectedItems():
            if isinstance(it, GeoItem):
                it.stroke_width = val
                it.update()

    def _apply_ink_width(self, val: float):
        ink = self._tm.all_tools().get("ink")
        if ink:
            ink.base_width = val

    def _selected_labels(self) -> list:
        return [it for it in self._scene.selectedItems()
                if hasattr(it, "apply_style_state")]

    def _apply_label_font(self, *_):
        if self._updating_font:
            return
        family = self._font_combo.currentFont().family()
        size = self._font_size_spin.value()
        labels = self._selected_labels()
        history = getattr(self._tm, '_history', None)
        for it in labels:
            old = it.style_state()
            new = (old[0], family, size)
            if history:
                history.push_label_style(it, old, new)
            else:
                it.apply_style_state(new)
        from items.point_label import PointLabelItem
        if not labels or not all(isinstance(it, PointLabelItem) for it in labels):
            from ui.label_dialog import remember_label_font
            remember_label_font(family, size)

    def _on_hide_btn(self):
        """Click nút Ẩn/Hiện trong panel."""
        selected = [it for it in self._scene.selectedItems()
                    if isinstance(it, GeoItem)]
        if not selected:
            self._hide_btn.setChecked(False)
            return
        want_hidden = self._hide_btn.isChecked()
        # Dùng history để có undo/redo (push_visibility tự gọi set_hidden qua redo)
        history = getattr(self._tm, '_history', None)
        if history:
            history.push_visibility(selected, want_hidden)
        else:
            for it in selected:
                it.set_hidden(want_hidden)
        # Cập nhật nhãn nút
        self._hide_btn.setText("👁  Hiện" if want_hidden else "👁  Ẩn")

    def _on_selection(self):
        try:
            selected = self._scene.selectedItems()
        except RuntimeError:
            return    # scene đã bị hủy (đang đóng app)
        if not selected:
            # Khi không có gì được chọn, reset nút về trạng thái mặc định
            self._hide_btn.setChecked(False)
            self._hide_btn.setText("👁  Ẩn")
            return
        labels = self._selected_labels()
        if labels:
            _, family, size = labels[0].style_state()
            self._updating_font = True
            self._font_combo.setCurrentFont(QFont(family))
            self._font_size_spin.setValue(size)
            self._updating_font = False
        it = selected[0]
        if isinstance(it, GeoItem):
            self._set_btn_color(it.color)
            self._width_spin.setValue(it.stroke_width)
            # Cập nhật nút ẩn/hiện theo trạng thái item đầu tiên
            hidden = it._is_hidden
            self._hide_btn.setChecked(hidden)
            self._hide_btn.setText("👁  Hiện" if hidden else "👁  Ẩn")
