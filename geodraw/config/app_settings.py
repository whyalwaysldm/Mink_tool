"""Đọc/ghi cài đặt ứng dụng từ config/settings.json."""
import json
from pathlib import Path

_CFG = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "initial_zoom_percent": 0,   # 0 = "vừa trang tự động"
    "label_font_family": "Times New Roman",
    "label_font_size": 12,
}


class AppSettings:
    """Singleton-style: mọi nơi đều gọi AppSettings.load() / .save()."""

    def __init__(self, data: dict):
        self.initial_zoom_percent: int = int(data.get(
            "initial_zoom_percent", _DEFAULTS["initial_zoom_percent"]))
        # Font mặc định cho nhãn mới (nhớ lựa chọn lần trước)
        self.label_font_family: str = str(data.get(
            "label_font_family", _DEFAULTS["label_font_family"]))
        self.label_font_size: int = int(data.get(
            "label_font_size", _DEFAULTS["label_font_size"]))

    # ── I/O ──────────────────────────────────────────────────────────────

    @classmethod
    def load(cls) -> "AppSettings":
        if _CFG.exists():
            try:
                return cls(json.loads(_CFG.read_text(encoding="utf-8")))
            except Exception:
                pass
        return cls(_DEFAULTS)

    def save(self) -> None:
        _CFG.write_text(
            json.dumps({
                "initial_zoom_percent": self.initial_zoom_percent,
                "label_font_family": self.label_font_family,
                "label_font_size": self.label_font_size,
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
