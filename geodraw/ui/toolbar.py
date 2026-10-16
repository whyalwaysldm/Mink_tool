from PyQt6.QtWidgets import (QToolBar, QToolButton, QButtonGroup, QMenu)
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtCore import Qt, QSize

# ── Danh sách tool cơ bản ────────────────────────────────────────────────────
BASIC_TOOLS = [
    ("select",   "↖",  "Chọn (Esc)"),
    ("point",    "•",  "Điểm (P)"),
    ("segment",  "╱",  "Đoạn thẳng (S)"),
    ("line",     "━",  "Đường thẳng (L)"),
    ("ray",      "→",  "Tia (R)"),
    ("circle",   "○",  "Đường tròn (C)"),
    ("arc",      "⌒",  "Cung (A)"),
    ("triangle", "△",  "Tam giác (T)"),
    ("polygon",  "⬡",  "Đa giác (G)"),
    # "mark" được thay bằng MarkPopupButton bên dưới
    ("label",    "T",  "Nhãn (B)"),
    ("ink",      "✏",  "Bút vẽ (I)"),
    ("erase",    "⌫",  "Xóa (E)"),
]

# ── Sub-mode ký hiệu (mode, count, icon, mô tả) ─────────────────────────────
MARK_SUBMODES = [
    ("equal",       1, "|",    "1 gạch — bằng nhau"),
    ("equal",       2, "||",   "2 gạch — bằng nhau"),
    ("equal",       3, "|||",  "3 gạch — bằng nhau"),
    ("equal",       4, "✕",    "Dấu × — bằng nhau"),
    ("parallel",    1, "▷",    "1 mũi tên — song song"),
    ("parallel",    2, "▷▷",   "2 mũi tên — song song"),
    ("angle",       1, "∠",    "Cung — ký hiệu góc"),
    ("right_angle", 1, "⊾",    "Góc vuông"),
]

# ── Hình đặc biệt — gom vào 1 nút popup ─────────────────────────────────────
SHAPE_TOOLS = [
    ("rectangle",               "▭",  "Hình chữ nhật (F1)"),
    ("square",                  "□",  "Hình vuông (F2)"),
    ("equilateral_triangle",    "▲",  "Tam giác đều (F3)"),
    ("right_triangle",          "◺",  "Tam giác vuông (F4)"),
    ("isosceles_right_triangle","◿",  "Tam giác vuông cân (F5)"),
    ("isosceles_triangle",      "🔺", "Tam giác cân (F6)"),
    ("rhombus",                 "◇",  "Hình thoi (F7)"),
    ("parallelogram",           "▱",  "Hình bình hành (F8)"),
    ("trapezoid",               "⏢",  "Hình thang (F9)"),
    ("hexagon",                 "⬡",  "Lục giác đều (F10)"),
    ("pentagon",                "⬠",  "Ngũ giác đều (F11)"),
]

# ── Tool dựng hình ──────────────────────────────────────────────────────────
GEO_TOOLS = [
    ("midpoint",       "M̈",  "Trung điểm (V)"),
    ("angle_bisector", "∠",  "Phân giác góc (J)"),
    ("circumcircle",   "⊙",  "Ngoại tiếp 3 điểm (K)"),
    ("rename_point",   "Aa", "Đặt tên điểm (N)"),
    ("measure",        "📐", "Đo đạc (D)"),
]


# ── Nút popup cho ký hiệu (mark) ─────────────────────────────────────────────
class MarkPopupButton(QToolButton):
    """Nút ký hiệu: click trái → dùng sub-mode đang chọn;
       click mũi tên → menu chọn sub-mode khác."""

    def __init__(self, tool_manager, group: QButtonGroup, parent=None):
        super().__init__(parent)
        self._tm = tool_manager
        # (mode, count) của sub-mode hiện tại
        self._current_mode  = "equal"
        self._current_count = 1

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        self.setFixedSize(48, 42)
        self.setCheckable(True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        menu = QMenu(self)
        for mode, count, icon, desc in MARK_SUBMODES:
            act = menu.addAction(f"{icon}  {desc}")
            act.setData((mode, count, icon))
            # Thêm separator sau nhóm equal và sau nhóm parallel
            if (mode, count) in (("equal", 4), ("parallel", 2)):
                menu.addSeparator()
        menu.triggered.connect(self._on_menu)
        self.setMenu(menu)

        self._update_display()
        self.clicked.connect(self._on_click)
        group.addButton(self)

        tool_manager.tool_changed.connect(self._on_tool_changed)

    # ── slots ────────────────────────────────────────────────────────────
    def _on_click(self):
        # push trước để signal tool_changed đọc đúng mode
        self._push_mode()
        self._tm.activate("mark")

    def _on_menu(self, action: QAction):
        mode, count, icon = action.data()
        self._current_mode  = mode
        self._current_count = count
        self._update_display()
        # push trước để signal tool_changed đọc đúng mode
        self._push_mode()
        self._tm.activate("mark")

    def _on_tool_changed(self, name: str):
        if name == "mark":
            self.setChecked(True)
            # Đồng bộ icon với mode hiện tại của MarkTool
            mark_tool = self._tm._tools.get("mark")
            if mark_tool:
                self._current_mode  = mark_tool.mode
                self._current_count = mark_tool.count
                self._update_display()
        else:
            self.setChecked(False)

    # ── helpers ──────────────────────────────────────────────────────────
    def _push_mode(self):
        """Truyền mode + count xuống MarkTool."""
        mark_tool = self._tm._tools.get("mark")
        if mark_tool:
            mark_tool.set_full_mode(self._current_mode, self._current_count)

    def _update_display(self):
        icon = next(
            (ic for m, c, ic, _ in MARK_SUBMODES
             if m == self._current_mode and c == self._current_count),
            "✓")
        desc = next(
            (d for m, c, _, d in MARK_SUBMODES
             if m == self._current_mode and c == self._current_count),
            "Ký hiệu")
        self.setText(icon)
        self.setToolTip(
            f"Ký hiệu — hiện tại: {desc}\n"
            "(M để cycle, hoặc click mũi tên để chọn)")


# ── Nút popup cho hình đặc biệt ──────────────────────────────────────────────
class ShapePopupButton(QToolButton):
    """Một nút duy nhất: click trái → dùng hình đang chọn;
       click mũi tên → menu chọn hình khác."""

    def __init__(self, tool_manager, shapes: list, group: QButtonGroup, parent=None):
        super().__init__(parent)
        self._tm = tool_manager
        self._shape_map = {s[0]: s for s in shapes}
        self._current = shapes[0][0]

        font = QFont()
        font.setPointSize(12)
        self.setFont(font)
        self.setFixedSize(48, 42)
        self.setCheckable(True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        # Build menu
        menu = QMenu(self)
        for name, icon, tooltip in shapes:
            act = menu.addAction(f"{icon}  {tooltip.split(' (')[0]}")
            act.setData(name)
        menu.triggered.connect(self._on_menu)
        self.setMenu(menu)

        self._update_display()
        self.clicked.connect(self._on_click)
        group.addButton(self)

        # React to external tool activations (e.g. F-key shortcuts)
        tool_manager.tool_changed.connect(self._on_tool_changed)

    # ── slots ────────────────────────────────────────────────────────────
    def _on_click(self):
        self._tm.activate(self._current)

    def _on_menu(self, action: QAction):
        name = action.data()
        self._current = name
        self._update_display()
        self._tm.activate(name)

    def _on_tool_changed(self, name: str):
        if name in self._shape_map:
            self._current = name
            self._update_display()
            self.setChecked(True)
        else:
            self.setChecked(False)

    # ── helpers ──────────────────────────────────────────────────────────
    def _update_display(self):
        s = self._shape_map[self._current]
        self.setText(s[1])
        self.setToolTip(f"Hình đặc biệt — hiện tại: {s[2].split(' (')[0]}\n"
                        f"(F1–F11 hoặc click mũi tên để chọn hình khác)")


# ── Thanh công cụ chính ──────────────────────────────────────────────────────
class ToolBar(QToolBar):

    def __init__(self, tool_manager, parent=None):
        super().__init__("Công cụ", parent)
        self._tm = tool_manager
        self._buttons: dict = {}
        self.setOrientation(Qt.Orientation.Vertical)
        self.setIconSize(QSize(36, 36))
        self.setMovable(False)
        self.setFloatable(False)

        font14 = QFont()
        font14.setPointSize(14)
        font11 = QFont()
        font11.setPointSize(11)

        self._group = QButtonGroup(self)
        self._group.setExclusive(True)

        # ── Section 1: Tool cơ bản ────────────────────────────────────
        for name, icon_text, tooltip in BASIC_TOOLS:
            btn = QToolButton()
            btn.setText(icon_text)
            btn.setFont(font14)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(42, 42)
            btn.clicked.connect(lambda _, n=name: tool_manager.activate(n))
            self._group.addButton(btn)
            self._buttons[name] = btn
            self.addWidget(btn)

            # Sau "polygon" → chèn nút mark popup
            if name == "polygon":
                mark_btn = MarkPopupButton(tool_manager, self._group, self)
                self._buttons["mark"] = mark_btn
                self.addWidget(mark_btn)

        # ── Section 2: Hình đặc biệt (popup button) ──────────────────
        self.addSeparator()
        shape_btn = ShapePopupButton(tool_manager, SHAPE_TOOLS, self._group, self)
        self.addWidget(shape_btn)
        # Map mọi tên hình → cùng nút (để _on_tool_changed tìm thấy)
        for name, _, _ in SHAPE_TOOLS:
            self._buttons[name] = shape_btn

        # ── Section 3: Tool dựng hình ─────────────────────────────────
        self.addSeparator()
        for name, icon_text, tooltip in GEO_TOOLS:
            btn = QToolButton()
            btn.setText(icon_text)
            btn.setFont(font11)
            btn.setToolTip(tooltip)
            btn.setCheckable(True)
            btn.setFixedSize(42, 42)
            btn.clicked.connect(lambda _, n=name: tool_manager.activate(n))
            self._group.addButton(btn)
            self._buttons[name] = btn
            self.addWidget(btn)

        tool_manager.tool_changed.connect(self._on_tool_changed)
        self._on_tool_changed("select")

    def _on_tool_changed(self, name: str):
        btn = self._buttons.get(name)
        if btn and not isinstance(btn, (ShapePopupButton, MarkPopupButton)):
            # ShapePopupButton / MarkPopupButton tự xử lý setChecked qua signal riêng
            btn.setChecked(True)
