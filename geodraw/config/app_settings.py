"""Đọc/ghi cài đặt ứng dụng từ config/settings.json."""
import json
from pathlib import Path

_CFG = Path(__file__).parent / "settings.json"

_DEFAULTS = {
    "initial_zoom_percent": 0,   # 0 = "vừa trang tự động"
}


class AppSettings:
    """Singleton-style: mọi nơi đều gọi AppSettings.load() / .save()."""

    def __init__(self, data: dict):
        self.initial_zoom_percent: int = int(data.get(
            "initial_zoom_percent", _DEFAULTS["initial_zoom_percent"]))

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
            }, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
