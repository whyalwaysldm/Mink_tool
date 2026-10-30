from PyQt6.QtWidgets import (QMainWindow, QApplication, QStatusBar,
                              QMenuBar, QMenu, QToolBar, QToolButton,
                              QButtonGroup, QLabel, QTabWidget, QMessageBox)
from PyQt6.QtGui import QKeyEvent, QAction, QFont
from PyQt6.QtCore import Qt, QTimer, QSize

from core.scene import GeoScene
from core.view import GeoView
from core.history import History
from core.style_manager import get_style_manager
from tools import ToolManager
from ui.toolbar import ToolBar
from ui.properties_panel import PropertiesPanel
from ui.shortcut_editor import ShortcutEditorDialog
from ui.settings_dialog import SettingsDialog
from ui.style_dialog import StyleDialog
from config.app_settings import AppSettings
from export.clipboard import render_to_clipboard
from export.file_export import save_png, save_svg, save_pdf
from utils.tablet import EraserAutoSwitch


class _Session:
    """Một phiên làm việc (1 tab): vùng vẽ + lịch sử hoàn tác riêng."""

    def __init__(self):
        self.history = History()
        self.scene = GeoScene(self.history)
        self.view = None              # GeoView — tạo sau khi có ToolManager


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.setWindowTitle("GeoDraw — Vẽ hình học")
        self.resize(1200, 800)

        first = _Session()
        self._tm = ToolManager(first.scene, first.history)
        first.scene.set_tool(self._tm.current_tool)
        self._style_mgr = get_style_manager()

        # Mỗi tab là một phiên làm việc (Ctrl+N → phiên mới)
        self._session_no = 0
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)
        self._tabs.setTabsClosable(True)
        self._tabs.setMovable(True)
        self._tabs.tabCloseRequested.connect(self._close_session)
        self._add_session(first)
        self._tabs.currentChanged.connect(self._on_tab_changed)
        self.setCentralWidget(self._tabs)

        # Toolbar công cụ (trái)
        self._toolbar = ToolBar(self._tm, self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self._toolbar)

        # Thanh preset kích thước (trên cùng)
        self._style_bar = self._build_style_bar()
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self._style_bar)

        # Properties dock
        self._props = PropertiesPanel(first.scene, self._tm, self)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._props)

        # Status bar
        self.setStatusBar(QStatusBar())
        self._tm.tool_changed.connect(self._on_tool_changed)
        self._tm.status_hint.connect(
            lambda msg: self.statusBar().showMessage(msg))
        self._on_tool_changed("select")

        # Eraser auto-switch
        self._eraser_filter = EraserAutoSwitch(self._tm, self)
        QApplication.instance().installEventFilter(self._eraser_filter)

        # Menu
        self._build_menu()

        # Activate default tool
        self._tm.activate("select")

        # Sau khi cửa sổ hiển thị: áp dụng zoom theo cài đặt
        QTimer.singleShot(80, self._apply_initial_zoom)

    # ── Phiên làm việc (tab) ────────────────────────────────────────────

    def _session(self) -> _Session:
        return self._tabs.currentWidget()._session

    @property
    def _scene(self):
        return self._session().scene

    @property
    def _history(self):
        return self._session().history

    @property
    def _view(self):
        return self._session().view

    def _add_session(self, sess: _Session) -> int:
        sess.view = GeoView(sess.scene, self._tm)
        sess.view._session = sess
        self._session_no += 1
        return self._tabs.addTab(sess.view, f"Phiên {self._session_no}")

    def _new_session(self):
        """Ctrl+N: mở phiên làm việc mới trong tab mới, phiên cũ giữ nguyên."""
        idx = self._add_session(_Session())
        self._tabs.setCurrentIndex(idx)
        QTimer.singleShot(0, self._apply_initial_zoom)
        self.statusBar().showMessage(
            f"✓ Đã mở {self._tabs.tabText(idx)} — các phiên cũ vẫn ở các tab trước",
            3000)

    def _on_tab_changed(self, idx: int):
        if idx < 0:
            return
        sess = self._tabs.widget(idx)._session
        self._tm.set_session(sess.scene, sess.history)
        self._props.set_scene(sess.scene)

    def _close_session(self, idx: int):
        if self._tabs.count() <= 1:
            self.statusBar().showMessage("Không thể đóng phiên cuối cùng", 2500)
            return
        view = self._tabs.widget(idx)
        from items.base import GeoItem
        if any(isinstance(it, GeoItem) for it in view._session.scene.items()):
            ans = QMessageBox.question(
                self, "Đóng phiên",
                f"Đóng {self._tabs.tabText(idx)}? Hình vẽ trong phiên này sẽ mất.")
            if ans != QMessageBox.StandardButton.Yes:
                return
        self._tabs.removeTab(idx)     # → currentChanged sang tab khác
        view._session.history.stack.clear()
        view.deleteLater()
        view._session.scene.deleteLater()

    def _build_menu(self):
        mb = self.menuBar()

        # File
        file_menu = mb.addMenu("Tệp")
        act_new = QAction("Phiên làm việc mới (Ctrl+N)", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(self._new_session)
        file_menu.addAction(act_new)
        file_menu.addSeparator()

        act_png = QAction("Lưu PNG (Ctrl+S)", self)
        act_png.setShortcut("Ctrl+S")
        act_png.triggered.connect(lambda: save_png(self._scene, self))
        file_menu.addAction(act_png)

        act_svg = QAction("Lưu SVG (Ctrl+Shift+S)", self)
        act_svg.setShortcut("Ctrl+Shift+S")
        act_svg.triggered.connect(lambda: save_svg(self._scene, self))
        file_menu.addAction(act_svg)

        act_pdf = QAction("Lưu PDF (Ctrl+P)", self)
        act_pdf.setShortcut("Ctrl+P")
        act_pdf.triggered.connect(self._save_pdf)
        file_menu.addAction(act_pdf)

        file_menu.addSeparator()
        act_quit = QAction("Thoát", self)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # Edit
        edit_menu = mb.addMenu("Sửa")
        act_undo = QAction("Hoàn tác (Ctrl+Z)", self)
        act_undo.setShortcut("Ctrl+Z")
        act_undo.triggered.connect(lambda: self._history.undo())
        edit_menu.addAction(act_undo)

        act_redo = QAction("Làm lại (Ctrl+Y)", self)
        act_redo.setShortcut("Ctrl+Y")
        act_redo.triggered.connect(lambda: self._history.redo())
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()
        act_copy = QAction("Copy hình → clipboard (Ctrl+C)", self)
        act_copy.setShortcut("Ctrl+C")
        act_copy.triggered.connect(self._copy_to_clipboard)
        edit_menu.addAction(act_copy)

        edit_menu.addSeparator()
        act_hide = QAction("Ẩn/Hiện đối tượng chọn (H)", self)
        act_hide.triggered.connect(self._toggle_hidden_selected)
        edit_menu.addAction(act_hide)

        act_show_all = QAction("Hiện tất cả đối tượng ẩn", self)
        act_show_all.triggered.connect(self._show_all_hidden)
        edit_menu.addAction(act_show_all)

        edit_menu.addSeparator()
        act_clear = QAction("Xóa tất cả", self)
        act_clear.triggered.connect(self._clear_all)
        edit_menu.addAction(act_clear)

        # View
        view_menu = mb.addMenu("Xem")
        act_zi = QAction("Phóng to (Ctrl+=)", self)
        act_zi.setShortcut("Ctrl+=")
        act_zi.triggered.connect(lambda: self._view.zoom_in())
        view_menu.addAction(act_zi)

        act_zo = QAction("Thu nhỏ (Ctrl+-)", self)
        act_zo.setShortcut("Ctrl+-")
        act_zo.triggered.connect(lambda: self._view.zoom_out())
        view_menu.addAction(act_zo)

        act_zf = QAction("Vừa màn hình (Ctrl+0)", self)
        act_zf.setShortcut("Ctrl+0")
        act_zf.triggered.connect(lambda: self._view.zoom_fit())
        view_menu.addAction(act_zf)

        view_menu.addSeparator()
        act_props = QAction("Bảng thuộc tính", self)
        act_props.setCheckable(True)
        act_props.setChecked(True)
        act_props.triggered.connect(
            lambda checked: self._props.setVisible(checked))
        view_menu.addAction(act_props)

        # Settings
        settings_menu = mb.addMenu("Cài đặt")

        act_gen = QAction("Cài đặt chung…", self)
        act_gen.triggered.connect(self._open_settings)
        settings_menu.addAction(act_gen)

        act_style = QAction("Kích thước hiển thị…", self)
        act_style.triggered.connect(self._open_style_dialog)
        settings_menu.addAction(act_style)

        settings_menu.addSeparator()

        act_sc = QAction("Cấu hình phím tắt…", self)
        act_sc.triggered.connect(self._open_shortcut_editor)
        settings_menu.addAction(act_sc)

    # ── Style preset bar ────────────────────────────────────────────────

    def _build_style_bar(self) -> QToolBar:
        """Xây dựng thanh công cụ chọn preset kích thước."""
        bar = QToolBar("Kích thước", self)
        bar.setMovable(False)
        bar.setFloatable(False)
        bar.setIconSize(QSize(28, 28))

        # Label
        lbl = QLabel("  Kích thước: ")
        lbl.setFont(QFont("Arial", 9))
        bar.addWidget(lbl)

        # Nhóm nút preset
        group = QButtonGroup(self)
        group.setExclusive(True)
        self._preset_btns: dict = {}

        font_sizes = {"Nhỏ": 8, "Vừa": 10, "To": 13}
        for name in self._style_mgr.preset_names:
            btn = QToolButton()
            btn.setText(name)
            f = QFont()
            f.setPointSize(font_sizes.get(name, 10))
            btn.setFont(f)
            btn.setCheckable(True)
            btn.setFixedSize(44, 30)
            preset = self._style_mgr.preset(name)
            btn.setToolTip(
                f"Preset <b>{name}</b><br>"
                f"Cỡ điểm: {preset['point_radius']} px &nbsp;|&nbsp; "
                f"Độ dày nét: {preset['stroke_width']} px"
            )
            btn.clicked.connect(lambda _, n=name: self._on_preset_click(n))
            group.addButton(btn)
            self._preset_btns[name] = btn
            bar.addWidget(btn)

        # Nút tùy chỉnh
        bar.addSeparator()
        edit_btn = QToolButton()
        edit_btn.setText("⚙")
        edit_btn.setToolTip("Tùy chỉnh preset kích thước…")
        edit_btn.setFixedSize(30, 30)
        edit_btn.clicked.connect(self._open_style_dialog)
        bar.addWidget(edit_btn)

        # Đồng bộ nút với preset hiện tại
        self._sync_style_bar()
        self._style_mgr.changed.connect(self._sync_style_bar)
        return bar

    def _on_preset_click(self, name: str):
        self._style_mgr.set_current(name)
        preset = self._style_mgr.preset(name)
        self.statusBar().showMessage(
            f"✓ Preset [{name}] — điểm {preset['point_radius']}px, "
            f"nét {preset['stroke_width']}px", 3000)

    def _sync_style_bar(self):
        """Cập nhật trạng thái checked và tooltip các nút sau khi preset thay đổi."""
        current = self._style_mgr.current_name
        for name, btn in self._preset_btns.items():
            btn.setChecked(name == current)
            preset = self._style_mgr.preset(name)
            btn.setToolTip(
                f"Preset <b>{name}</b><br>"
                f"Cỡ điểm: {preset['point_radius']} px &nbsp;|&nbsp; "
                f"Độ dày nét: {preset['stroke_width']} px"
            )

    def _open_style_dialog(self):
        dlg = StyleDialog(self._style_mgr, self)
        dlg.exec()
        self._sync_style_bar()   # cập nhật tooltip sau khi chỉnh

    def _save_pdf(self):
        ok = save_pdf(self._scene, self)
        if ok:
            self.statusBar().showMessage("✓ Đã lưu PDF thành công", 3000)
        else:
            self.statusBar().showMessage("Hủy lưu PDF", 2000)

    def _copy_to_clipboard(self):
        if self._scene.selectedItems():
            self._scene.clearSelection()
        ok = render_to_clipboard(self._scene)
        if ok:
            self.statusBar().showMessage(
                "✓ Đã copy hình — dán vào Scrble Ink bằng Ctrl+V", 3000)
        else:
            self.statusBar().showMessage("Chưa có hình để copy", 2000)

    def _toggle_hidden_selected(self):
        """Ẩn/Hiện các item đang được chọn (giống phím H trong SelectTool)."""
        from items.base import GeoItem
        selected = [it for it in self._scene.selectedItems()
                    if isinstance(it, GeoItem)]
        if selected:
            any_visible = any(not it._is_hidden for it in selected)
            self._history.push_visibility(selected, any_visible)
            state = "ẩn" if any_visible else "hiện"
            self.statusBar().showMessage(
                f"✓ Đã {state} {len(selected)} đối tượng", 2500)
        else:
            self.statusBar().showMessage("Chưa chọn đối tượng nào", 2000)

    def _show_all_hidden(self):
        """Hiện tất cả đối tượng đang bị ẩn."""
        from items.base import GeoItem
        hidden = [it for it in self._scene.items()
                  if isinstance(it, GeoItem) and it._is_hidden]
        if hidden:
            self._history.push_visibility(hidden, False)
            self.statusBar().showMessage(
                f"✓ Đã hiện {len(hidden)} đối tượng bị ẩn", 2500)
        else:
            self.statusBar().showMessage("Không có đối tượng nào đang bị ẩn", 2000)

    def _clear_all(self):
        self._scene.clear()

    def _open_settings(self):
        from PyQt6.QtWidgets import QDialog
        dlg = SettingsDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._apply_initial_zoom()
            self.statusBar().showMessage("✓ Đã lưu và áp dụng zoom", 3000)

    def _apply_initial_zoom(self):
        """Áp dụng zoom ban đầu theo cài đặt (gọi sau khi cửa sổ hiện)."""
        pct = AppSettings.load().initial_zoom_percent
        if pct > 0:
            self._view.set_zoom_percent(pct)
        else:
            self._view.zoom_fit()

    def _open_shortcut_editor(self):
        dlg = ShortcutEditorDialog(self._tm, self)
        dlg.exec()

    def _on_tool_changed(self, name: str):
        labels = {
            "select": "↖ Chọn", "point": "• Điểm", "segment": "╱ Đoạn thẳng",
            "line": "━ Đường thẳng", "ray": "→ Tia", "circle": "○ Đường tròn",
            "arc": "⌒ Cung", "triangle": "△ Tam giác", "polygon": "⬡ Đa giác",
            "mark": "✓ Ký hiệu", "label": "T Nhãn",
            "ink": "✏ Bút vẽ", "erase": "⌫ Xóa",
            # Geometry tools
            "midpoint": "M̈ Trung điểm", "angle_bisector": "∠ Phân giác",
            "parallel": "∥ Đường song song", "perpendicular": "⊥ Đường vuông góc",
            "compass": "◎ Đường tròn bán kính = đoạn",
            "tangent_circle": "⦾ Đường tròn tiếp xúc",
            "point_reflect": "⊕ Đối xứng tâm", "axis_reflect": "⇋ Đối xứng trục",
            "rotate": "↻ Phép quay", "homothety": "⤢ Phép vị tự",
            "circumcircle": "⊙ Ngoại tiếp", "rename_point": "Aa Đặt tên điểm",
            "measure": "📐 Đo đạc",
            # Shape tools
            "rectangle": "▭ Hình chữ nhật", "square": "□ Hình vuông",
            "equilateral_triangle": "▲ Tam giác đều",
            "right_triangle": "◺ Tam giác vuông",
            "isosceles_right_triangle": "◿ Tam giác vuông cân",
            "isosceles_triangle": "🔺 Tam giác cân",
            "rhombus": "◇ Hình thoi", "parallelogram": "▱ Hình bình hành",
            "trapezoid": "⏢ Hình thang", "hexagon": "⬡ Lục giác đều",
            "pentagon": "⬠ Ngũ giác đều",
        }
        self.statusBar().showMessage(f"Công cụ: {labels.get(name, name)}")
        view = self._view
        tool = self._tm.current_tool
        view.viewport().setCursor(tool.cursor)

    # ── Keyboard routing ────────────────────────────────────────────────
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        mod = event.modifiers()

        # Build key string matching shortcuts.json
        parts = []
        if mod & Qt.KeyboardModifier.ControlModifier:
            parts.append("Ctrl")
        if mod & Qt.KeyboardModifier.ShiftModifier:
            parts.append("Shift")
        if mod & Qt.KeyboardModifier.AltModifier:
            parts.append("Alt")

        key_name = self._key_name(key)
        if key_name:
            parts.append(key_name)
        key_str = "+".join(parts) if parts else ""

        action = self._tm.resolve_shortcut(key_str)
        if action:
            self._dispatch_action(action)
            return

        # Forward to active tool
        self._tm.current_tool.key_press(key, mod)
        super().keyPressEvent(event)

    def _key_name(self, key) -> str:
        from PyQt6.QtCore import Qt
        special = {
            Qt.Key.Key_Escape: "Escape",
            Qt.Key.Key_Delete: "Delete",
            Qt.Key.Key_Backspace: "Backspace",
            Qt.Key.Key_Return: "Return",
            Qt.Key.Key_Enter: "Enter",
            Qt.Key.Key_Equal: "=",
            Qt.Key.Key_Minus: "-",
            # Function keys (F1–F12)
            Qt.Key.Key_F1:  "F1",  Qt.Key.Key_F2:  "F2",
            Qt.Key.Key_F3:  "F3",  Qt.Key.Key_F4:  "F4",
            Qt.Key.Key_F5:  "F5",  Qt.Key.Key_F6:  "F6",
            Qt.Key.Key_F7:  "F7",  Qt.Key.Key_F8:  "F8",
            Qt.Key.Key_F9:  "F9",  Qt.Key.Key_F10: "F10",
            Qt.Key.Key_F11: "F11", Qt.Key.Key_F12: "F12",
        }
        if key in special:
            return special[key]
        if Qt.Key.Key_A <= key <= Qt.Key.Key_Z:
            return chr(key)
        return ""

    def _dispatch_action(self, action: str):
        tool_names = set(self._tm.all_tools().keys())
        if action in tool_names:
            self._tm.activate(action)
        elif action == "undo":
            self._history.undo()
        elif action == "redo":
            self._history.redo()
        elif action == "copy_to_clipboard":
            self._copy_to_clipboard()
        elif action == "save_png":
            save_png(self._scene, self)
        elif action == "save_svg":
            save_svg(self._scene, self)
        elif action == "save_pdf":
            self._save_pdf()
        elif action == "delete_selected":
            from items.shape import expand_for_delete
            selected = expand_for_delete(self._scene.selectedItems())
            if selected:
                self._history.push_remove(self._scene, selected)
        elif action == "zoom_in":
            self._view.zoom_in()
        elif action == "zoom_out":
            self._view.zoom_out()
        elif action == "zoom_fit":
            self._view.zoom_fit()
