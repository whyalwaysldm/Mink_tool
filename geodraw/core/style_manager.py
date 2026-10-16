"""
StyleManager — quản lý preset kích thước hiển thị điểm / nét vẽ.

Ba preset mặc định: Nhỏ / Vừa / To.
Người dùng có thể chỉnh từng preset; cài đặt lưu vào config/style.json.

Dùng dưới dạng singleton qua  get_style_manager().
"""
import json
from pathlib import Path
from collections import OrderedDict

from PyQt6.QtCore import QObject, pyqtSignal


# ── Mặc định ──────────────────────────────────────────────────────────────────

_DEFAULT_PRESETS: "OrderedDict[str, dict]" = OrderedDict([
    ("Nhỏ", {"point_radius": 2.5, "stroke_width": 1.2}),
    ("Vừa", {"point_radius": 3.5, "stroke_width": 1.8}),
    ("To",  {"point_radius": 5.0, "stroke_width": 3.0}),
])
_DEFAULT_CURRENT = "Vừa"
_CFG_PATH = Path(__file__).parent.parent / "config" / "style.json"


# ── Class chính ───────────────────────────────────────────────────────────────

class StyleManager(QObject):
    """Quản lý preset kích thước; phát tín hiệu `changed` khi preset thay đổi."""

    changed = pyqtSignal()          # phát sau mỗi lần đổi preset / tùy chỉnh

    def __init__(self):
        super().__init__()
        self._presets: "OrderedDict[str, dict]" = OrderedDict(
            (k, dict(v)) for k, v in _DEFAULT_PRESETS.items()
        )
        self._current: str = _DEFAULT_CURRENT
        self._load()

    # ── Truy cập giá trị hiện tại ────────────────────────────────────────

    @property
    def point_radius(self) -> float:
        return self._presets[self._current]["point_radius"]

    @property
    def stroke_width(self) -> float:
        return self._presets[self._current]["stroke_width"]

    @property
    def current_name(self) -> str:
        return self._current

    @property
    def preset_names(self) -> list:
        return list(self._presets.keys())

    def preset(self, name: str) -> dict:
        """Trả về bản sao dict của preset theo tên."""
        return dict(self._presets.get(name, {}))

    @property
    def default_presets(self) -> dict:
        return {k: dict(v) for k, v in _DEFAULT_PRESETS.items()}

    # ── Thay đổi ─────────────────────────────────────────────────────────

    def set_current(self, name: str):
        """Chuyển sang preset name (nếu tồn tại). Phát changed + lưu file."""
        if name in self._presets and name != self._current:
            self._current = name
            self._save()
            self.changed.emit()

    def update_preset(self, name: str, point_radius: float, stroke_width: float):
        """Cập nhật giá trị cho preset name. Phát changed nếu đang dùng preset đó."""
        self._presets[name] = {
            "point_radius": round(point_radius, 2),
            "stroke_width": round(stroke_width, 2),
        }
        self._save()
        if name == self._current:
            self.changed.emit()

    def reset_to_defaults(self):
        """Khôi phục tất cả preset về mặc định."""
        self._presets = OrderedDict((k, dict(v)) for k, v in _DEFAULT_PRESETS.items())
        self._current = _DEFAULT_CURRENT
        self._save()
        self.changed.emit()

    # ── Persistence ───────────────────────────────────────────────────────

    def _load(self):
        if not _CFG_PATH.exists():
            return
        try:
            data = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
            for name, vals in data.get("presets", {}).items():
                if "point_radius" in vals and "stroke_width" in vals:
                    self._presets[name] = {
                        "point_radius": float(vals["point_radius"]),
                        "stroke_width": float(vals["stroke_width"]),
                    }
            cur = data.get("current", _DEFAULT_CURRENT)
            if cur in self._presets:
                self._current = cur
        except Exception:
            pass

    def _save(self):
        try:
            _CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
            _CFG_PATH.write_text(
                json.dumps({
                    "current": self._current,
                    "presets": {k: dict(v) for k, v in self._presets.items()},
                }, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass


# ── Singleton ────────────────────────────────────────────────────────────────

_instance: "StyleManager | None" = None


def get_style_manager() -> StyleManager:
    global _instance
    if _instance is None:
        _instance = StyleManager()
    return _instance
