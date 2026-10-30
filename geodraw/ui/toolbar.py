from PyQt6.QtWidgets import (QToolBar, QToolButton, QButtonGroup, QMenu)
from PyQt6.QtGui import QFont, QAction
from PyQt6.QtCore import Qt, QSize

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
    ("rhombus",                 "◇",  "Hình thoi (F7)"),
    ("parallelogram",           "▱",  "Hình bình hành (F8)"),
    ("trapezoid",               "⏢",  "Hình thang (F9)"),
    ("hexagon",                 "⬡",  "Lục giác đều (F10)"),
    ("pentagon",                "⬠",  "Ngũ giác đều (F11)"),
]

# ── Các ô trên thanh công cụ ────────────────────────────────────────────────
# Mỗi ô là 1 công cụ đơn, hoặc 1 nhóm công cụ gần giống nhau.
# Nhóm: click → dùng công cụ đang hiện trên ô; click lần nữa (hoặc mũi tên,
# hoặc chuột phải) → menu đổi sang công cụ khác trong nhóm.
# Phần tử None trong nhóm = đường kẻ ngăn cách trong menu.
TOOLBAR_LAYOUT = [
    ("tool",  ("select",   "↖",  "Chọn (Esc)")),
    ("group", ("Điểm", [
        ("point",          "•",  "Điểm (P)"),
        ("midpoint",       "M̈",  "Trung điểm (V)"),
    ])),
    ("group", ("Đường", [
        ("segment",        "╱",  "Đoạn thẳng (S)"),
        ("line",           "━",  "Đường thẳng (L)"),
        ("ray",            "→",  "Tia (R)"),
        None,
        ("angle_bisector", "∠",  "Phân giác góc (J)"),
        ("parallel",       "∥",  "Đường song song qua 1 điểm (Q)"),
        ("perpendicular",  "⊥",  "Đường vuông góc qua 1 điểm (W)"),
    ])),
    ("group", ("Đường tròn", [
        ("circle",         "○",  "Đường tròn (C)"),
        ("arc",            "⌒",  "Cung (A)"),
        ("circumcircle",   "⊙",  "Đường tròn ngoại tiếp 3 điểm (K)"),
        ("compass",        "◎",  "Đường tròn tâm + bán kính bằng đoạn thẳng (O)"),
        ("tangent_circle", "⦾",  "Đường tròn tiếp xúc 2 đường thẳng và 1 đường tròn (U)"),
    ])),
    ("group", ("Tam giác / đa giác", [
        ("triangle",       "△",  "Tam giác (T)"),
        ("equilateral_triangle", "▲", "Tam giác đều (F3)"),
        ("isosceles_triangle",   "🔺", "Tam giác cân (F6)"),
        ("right_triangle",       "◺", "Tam giác vuông (F4)"),
        ("isosceles_right_triangle", "◿", "Tam giác vuông cân (F5)"),
        None,
        ("polygon",        "⬡",  "Đa giác (G)"),
    ])),
    ("group", ("Hình đặc biệt", SHAPE_TOOLS)),
    ("mark",  None),             # ký hiệu bằng nhau / song song / góc
    ("separator", None),
    ("group", ("Chữ", [
        ("label",          "T",  "Nhãn (B)"),
        ("rename_point",   "Aa", "Đặt tên điểm (N)"),
    ])),
    ("tool",  ("measure",  "📐", "Đo đạc (D)")),
    ("group", ("Biến hình", [
        ("point_reflect",  "⊕",  "Đối xứng tâm"),
        ("axis_reflect",   "⇋",  "Đối xứng trục"),
        ("rotate",         "↻",  "Phép quay"),
        ("homothety",      "⤢",  "Phép vị tự"),
    ])),
    ("separator", None),
    ("tool",  ("ink",      "✏",  "Bút vẽ (I)")),
    ("tool",  ("erase",    "⌫",  "Xóa (E)")),
]


# ── Nút nhóm: nhiều công cụ chung 1 ô ───────────────────────────────────────
class ToolGroupButton(QToolButton):
    """Một ô cho cả nhóm công cụ.
       Click → dùng công cụ đang hiện; click lại khi đang dùng / mũi tên /
       chuột phải → menu chọn công cụ khác trong nhóm."""

    def __init__(self, tool_manager, title: str, tools: list,
                 group: QButtonGroup, parent=None):
        super().__init__(parent)
        self._tm = tool_manager
        self._title = title
        self._was_active = False
        entries = [t for t in tools if t is not None]
        self._tool_map = {t[0]: t for t in entries}
        self._current = entries[0][0]

        font = QFont()
        font.setPointSize(13)
        self.setFont(font)
        self.setFixedSize(48, 42)
        self.setCheckable(True)
        self.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)

        menu = QMenu(self)
        for t in tools:
            if t is None:
                menu.addSeparator()
                continue
            name, icon, tooltip = t
            act = menu.addAction(f"{icon}   {tooltip}")
            act.setData(name)
        menu.triggered.connect(self._on_menu)
        self.setMenu(menu)

        self._update_display()
        self.pressed.connect(self._on_pressed)
        self.clicked.connect(self._on_click)
        group.addButton(self)
        tool_manager.tool_changed.connect(self._on_tool_changed)

    def tool_names(self) -> list:
        return list(self._tool_map)

    # ── slots ────────────────────────────────────────────────────────────
    def _on_pressed(self):
        # Ghi nhận trạng thái TRƯỚC khi click làm đổi checked
        self._was_active = self._tm.current_name in self._tool_map

    def _on_click(self):
        if self._was_active:
            # Đang dùng nhóm này → click lần nữa để đổi công cụ
            self.setChecked(True)
            self.showMenu()
            return
        self._tm.activate(self._current)

    def contextMenuEvent(self, event):
        self.showMenu()

    def _on_menu(self, action: QAction):
        name = action.data()
        self._current = name
        self._update_display()
        self._tm.activate(name)

    def _on_tool_changed(self, name: str):
        if name in self._tool_map:
            self._current = name
            self._update_display()
            self.setChecked(True)
        else:
            self.setChecked(False)

    # ── helpers ──────────────────────────────────────────────────────────
    def _update_display(self):
        _, icon, tooltip = self._tool_map[self._current]
        self.setText(icon)
        self.setToolTip(f"{self._title} — đang chọn: {tooltip}\n"
                        "(click lần nữa hoặc click mũi tên để đổi)")


# ── Nút popup cho ký hiệu (mark) ─────────────────────────────────────────────
class MarkPopupButton(QToolButton):
    """Nút ký hiệu: click → dùng sub-mode đang chọn;
       click lại khi đang dùng / mũi tên / chuột phải → menu chọn sub-mode khác."""

    def __init__(self, tool_manager, group: QButtonGroup, parent=None):
        super().__init__(parent)
        self._tm = tool_manager
        self._was_active = False
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
        self.pressed.connect(self._on_pressed)
        self.clicked.connect(self._on_click)
        group.addButton(self)

        tool_manager.tool_changed.connect(self._on_tool_changed)

    # ── slots ────────────────────────────────────────────────────────────
    def _on_pressed(self):
        self._was_active = self._tm.current_name == "mark"

    def contextMenuEvent(self, event):
        self.showMenu()

    def _on_click(self):
        if self._was_active:
            # Đang dùng ký hiệu → click lần nữa để đổi loại
            self.setChecked(True)
            self.showMenu()
            return
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
            "(M để đổi nhanh, click lần nữa hoặc click mũi tên để chọn)")


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

        for kind, spec in TOOLBAR_LAYOUT:
            if kind == "separator":
                self.addSeparator()
            elif kind == "tool":
                name, icon_text, tooltip = spec
                btn = QToolButton()
                btn.setText(icon_text)
                btn.setFont(font14 if len(icon_text) == 1 else font11)
                btn.setToolTip(tooltip)
                btn.setCheckable(True)
                btn.setFixedSize(48, 42)
                btn.clicked.connect(lambda _, n=name: tool_manager.activate(n))
                self._group.addButton(btn)
                self._buttons[name] = btn
                self.addWidget(btn)
            elif kind == "group":
                title, tools = spec
                btn = ToolGroupButton(tool_manager, title, tools,
                                      self._group, self)
                self.addWidget(btn)
                # Map mọi tên công cụ trong nhóm → cùng nút
                for name in btn.tool_names():
                    self._buttons[name] = btn
            elif kind == "mark":
                btn = MarkPopupButton(tool_manager, self._group, self)
                self._buttons["mark"] = btn
                self.addWidget(btn)

        tool_manager.tool_changed.connect(self._on_tool_changed)
        self._on_tool_changed("select")

    def _on_tool_changed(self, name: str):
        btn = self._buttons.get(name)
        if btn and not isinstance(btn, (ToolGroupButton, MarkPopupButton)):
            # ToolGroupButton / MarkPopupButton tự xử lý setChecked qua signal riêng
            btn.setChecked(True)
