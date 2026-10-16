from PyQt6.QtWidgets import (QDockWidget, QWidget, QVBoxLayout, QHBoxLayout,
                              QLabel, QPushButton, QSlider, QColorDialog,
                              QDoubleSpinBox)
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
        selected = self._scene.selectedItems()
        if not selected:
            # Khi không có gì được chọn, reset nút về trạng thái mặc định
            self._hide_btn.setChecked(False)
            self._hide_btn.setText("👁  Ẩn")
            return
        it = selected[0]
        if isinstance(it, GeoItem):
            self._set_btn_color(it.color)
            self._width_spin.setValue(it.stroke_width)
            # Cập nhật nút ẩn/hiện theo trạng thái item đầu tiên
            hidden = it._is_hidden
            self._hide_btn.setChecked(hidden)
            self._hide_btn.setText("👁  Hiện" if hidden else "👁  Ẩn")
