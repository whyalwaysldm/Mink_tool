import math
from PyQt6.QtCore import Qt, QPointF
from .base_tool import BaseTool
from items.segment import SegmentItem
from items.point import PointItem
from items.marks import AngleMarkItem, RightAngleMarkItem, EqualMarkItem, ParallelMarkItem


class MarkTool(BaseTool):
    """
    Ký hiệu hình học trên đoạn / góc / điểm.

    Full-mode list (dùng phím M để cycle):
        equal/1  → 1 gạch   equal/2  → 2 gạch   equal/3  → 3 gạch
        equal/4  → dấu ×    parallel/1 → 1 mũi tên   parallel/2 → 2 mũi tên
        angle/1  → cung góc   right_angle/1 → góc vuông
    """
    name = "mark"

    # (mode, count) — thứ tự cycle khi bấm M
    _FULL_MODES = [
        ("equal",       1),
        ("equal",       2),
        ("equal",       3),
        ("equal",       4),
        ("parallel",    1),
        ("parallel",    2),
        ("angle",       1),
        ("right_angle", 1),
    ]
    _LABELS = {
        ("equal",       1): "1 gạch (bằng nhau)",
        ("equal",       2): "2 gạch (bằng nhau)",
        ("equal",       3): "3 gạch (bằng nhau)",
        ("equal",       4): "Dấu × (bằng nhau)",
        ("parallel",    1): "1 mũi tên (song song)",
        ("parallel",    2): "2 mũi tên (song song)",
        ("angle",       1): "Cung góc",
        ("right_angle", 1): "Góc vuông",
    }

    def __init__(self, scene, history, tool_manager):
        super().__init__(scene, history, tool_manager)
        self._full_idx = 0
        self._first_item = None   # dùng cho angle / right_angle (3-click)

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def mode(self) -> str:
        return self._FULL_MODES[self._full_idx][0]

    @property
    def count(self) -> int:
        return self._FULL_MODES[self._full_idx][1]

    # back-compat aliases
    @property
    def equal_count(self) -> int:
        m, c = self._FULL_MODES[self._full_idx]
        return c if m == "equal" else 1

    @property
    def parallel_count(self) -> int:
        m, c = self._FULL_MODES[self._full_idx]
        return c if m == "parallel" else 1

    # ── API dùng bởi toolbar ──────────────────────────────────────────────

    def set_full_mode(self, mode: str, count: int = 1):
        """Đặt mode + count từ bên ngoài (toolbar popup, shortcut…)."""
        key = (mode, count)
        if key in self._FULL_MODES:
            self._full_idx = self._FULL_MODES.index(key)
            self._first_item = None
            self._emit_hint()

    # ── Tool lifecycle ─────────────────────────────────────────────────────

    def activate(self):
        self._first_item = None
        self._emit_hint()

    def deactivate(self):
        self._first_item = None

    # ── Event ─────────────────────────────────────────────────────────────

    def press(self, pos: QPointF, button, modifiers):
        if button != Qt.MouseButton.LeftButton:
            return
        item = self._item_at(pos)
        if item is None:
            return

        mode = self.mode

        # ── Equal / Parallel — click vào đoạn thẳng ──────────────────
        if mode == "equal":
            if isinstance(item, SegmentItem):
                # Xóa mark cũ trên đoạn này (nếu có) trước khi thêm mới
                self._replace_marks_on(item)

                auto = self._auto_equal_count(item)
                count = auto if auto is not None else self.equal_count
                mark = EqualMarkItem(item, count=count)
                self.scene.addItem(mark)
                self.history.push_add(self.scene, mark)
                if auto is not None:
                    self.tm.status_hint.emit(
                        f"✓ Tự động đánh dấu: {count} gạch (khớp độ dài đoạn đã có)")
                else:
                    label = self._LABELS[self._FULL_MODES[self._full_idx]]
                    self.tm.status_hint.emit(f"✓ Đã thêm ký hiệu: {label}")

        elif mode == "parallel":
            if isinstance(item, SegmentItem):
                # Xóa mark cũ trên đoạn này (nếu có) trước khi thêm mới
                self._replace_marks_on(item)

                mark = ParallelMarkItem(item, count=self.parallel_count)
                self.scene.addItem(mark)
                self.history.push_add(self.scene, mark)
                label = self._LABELS[self._FULL_MODES[self._full_idx]]
                self.tm.status_hint.emit(f"✓ Đã thêm ký hiệu: {label}")

        # ── Right angle — click 3 điểm: điểm góc → cạnh 1 → cạnh 2 ──
        elif mode == "right_angle":
            if isinstance(item, PointItem):
                if self._first_item is None:
                    self._first_item = item
                    self.tm.status_hint.emit(
                        "Góc vuông: chọn điểm cạnh 1")
                else:
                    vertex = self._first_item
                    self._first_item = None
                    # Tìm điểm thứ 3 trên đoạn khác qua vertex (nếu có)
                    # Đơn giản: dùng item và vertex làm 2 cạnh;
                    # cần 1 điểm thứ ba → dùng lại vertex làm p2 tạm thời
                    mark = RightAngleMarkItem(vertex, item, vertex)
                    self.scene.addItem(mark)
                    self.history.push_add(self.scene, mark)
                    self.tm.status_hint.emit("✓ Đã thêm ký hiệu góc vuông")

        # ── Angle — click 3 điểm: điểm 1 (cạnh) → đỉnh → điểm 2 ────
        elif mode == "angle":
            if isinstance(item, PointItem):
                if self._first_item is None:
                    self._first_item = item
                    self.tm.status_hint.emit(
                        "Cung góc: chọn đỉnh góc")
                else:
                    p1     = self._first_item
                    vertex = item
                    self._first_item = vertex
                    self.tm.status_hint.emit(
                        "Cung góc: chọn điểm cạnh 2")
                    # Lần click thứ 3 sẽ hoàn tất
                    if hasattr(self, '_angle_p1'):
                        real_p1 = self._angle_p1
                        del self._angle_p1
                        mark = AngleMarkItem(vertex, real_p1, p1)
                        self.scene.addItem(mark)
                        self.history.push_add(self.scene, mark)
                        self._first_item = None
                        self.tm.status_hint.emit("✓ Đã thêm ký hiệu cung góc")
                    else:
                        self._angle_p1 = p1
                        self._first_item = vertex

    def _replace_marks_on(self, seg: SegmentItem):
        """
        Xóa tất cả EqualMarkItem / ParallelMarkItem đang gắn vào seg
        và ghi vào history để undo được.
        Gọi trước khi thêm mark mới để tránh chồng 2 dấu lên nhau.
        """
        old = [it for it in self.scene.items()
               if isinstance(it, (EqualMarkItem, ParallelMarkItem))
               and it.seg is seg]
        if old:
            self.history.push_remove(self.scene, old)

    def _item_at(self, pos: QPointF):
        """
        Trả về GeoItem ở trên cùng tại pos, bỏ qua các item UI
        (SnapIndicator, ghost cursor…) vốn có Z cao nhưng không phải hình học.
        """
        from items.base import GeoItem
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QTransform
        view = self.scene.views()[0] if self.scene.views() else None
        t = view.transform() if view else QTransform()
        for item in self.scene.items(
                pos,
                Qt.ItemSelectionMode.IntersectsItemShape,
                Qt.SortOrder.DescendingOrder,
                t):
            if isinstance(item, GeoItem):
                return item
        return None

    @staticmethod
    def _seg_len(seg: SegmentItem) -> float:
        sp1, sp2 = seg.p1.scenePos(), seg.p2.scenePos()
        dx, dy = sp2.x() - sp1.x(), sp2.y() - sp1.y()
        return math.sqrt(dx * dx + dy * dy)

    def _auto_equal_count(self, seg: SegmentItem) -> "int | None":
        """
        Tìm EqualMarkItem đã có trong scene thuộc đoạn khác cùng độ dài.
        Trả về count của mark đó (để tự động đồng bộ ký hiệu),
        hoặc None nếu không tìm thấy.
        """
        target = self._seg_len(seg)
        if target < 1e-6:
            return None
        TOLERANCE = 1.0          # px — sai số chấp nhận được
        for item in self.scene.items():
            if not isinstance(item, EqualMarkItem):
                continue
            if item.seg is seg:  # bỏ qua chính đoạn đang xét
                continue
            other = self._seg_len(item.seg)
            if abs(other - target) <= TOLERANCE:
                return item.count
        return None

    def key_press(self, key, modifiers):
        if key == Qt.Key.Key_M:
            self._full_idx = (self._full_idx + 1) % len(self._FULL_MODES)
            self._first_item = None
            self._emit_hint()
        elif key == Qt.Key.Key_Escape:
            self._first_item = None
            if hasattr(self, '_angle_p1'):
                del self._angle_p1

    # ── helpers ───────────────────────────────────────────────────────────

    def _emit_hint(self):
        label = self._LABELS.get(self._FULL_MODES[self._full_idx], "")
        if self.mode in ("equal", "parallel"):
            self.tm.status_hint.emit(
                f"Ký hiệu [{label}]: click vào đoạn thẳng")
        elif self.mode == "right_angle":
            self.tm.status_hint.emit(
                f"Ký hiệu [{label}]: click điểm góc, rồi điểm cạnh")
        else:
            self.tm.status_hint.emit(
                f"Ký hiệu [{label}]: click điểm cạnh 1, đỉnh, cạnh 2")
