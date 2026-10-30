import json
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal

from .select_tool import SelectTool
from .point_tool import PointTool
from .segment_tool import SegmentTool
from .line_tool import LineTool, RayTool
from .circle_tool import CircleTool
from .arc_tool import ArcTool
from .polygon_tool import PolygonTool, TriangleTool
from .mark_tool import MarkTool
from .label_tool import LabelTool
from .ink_tool import InkTool
from .erase_tool import EraseTool
from .shape_tool import ALL_SHAPE_TOOLS
from .midpoint_tool import MidpointTool
from .angle_bisector_tool import AngleBisectorTool
from .circumcircle_tool import CircumcircleTool
from .rename_point_tool import RenamePointTool
from .measure_tool import MeasureTool
from .tangent_circle_tool import TangentCircleTool
from .parallel_tool import ParallelTool, PerpendicularTool, CompassTool
from .transform_tool import (PointReflectTool, AxisReflectTool,
                             RotateTool, HomothetyTool)

_DEFAULT_SHORTCUTS = {
    "Escape": "select", "S": "segment", "L": "line", "R": "ray",
    "C": "circle", "A": "arc", "P": "point", "T": "triangle",
    "G": "polygon", "M": "mark", "I": "ink", "E": "erase", "B": "label",
    # Geometry construction
    "V": "midpoint", "J": "angle_bisector",
    "K": "circumcircle", "N": "rename_point",
    "D": "measure",
    "Q": "parallel", "W": "perpendicular", "O": "compass",
    "U": "tangent_circle",
    # Hình preset
    "F1": "rectangle", "F2": "square",
    "F3": "equilateral_triangle", "F4": "right_triangle",
    "F5": "isosceles_right_triangle", "F6": "isosceles_triangle",
    "F7": "rhombus", "F8": "parallelogram",
    "F9": "trapezoid", "F10": "hexagon", "F11": "pentagon",
}


class ToolManager(QObject):
    tool_changed = pyqtSignal(str)
    status_hint  = pyqtSignal(str)   # trạng thái hướng dẫn cho status bar

    def __init__(self, scene, history):
        super().__init__()
        self._scene = scene
        self._history = history

        def mk(cls):
            return cls(scene, history, self)

        self._tools = {
            "select":   mk(SelectTool),
            "point":    mk(PointTool),
            "segment":  mk(SegmentTool),
            "line":     mk(LineTool),
            "ray":      mk(RayTool),
            "circle":   mk(CircleTool),
            "arc":      mk(ArcTool),
            "polygon":  mk(PolygonTool),
            "triangle": mk(TriangleTool),
            "mark":     mk(MarkTool),
            "label":    mk(LabelTool),
            "ink":      mk(InkTool),
            "erase":    mk(EraseTool),
        }
        for cls in ALL_SHAPE_TOOLS:
            self._tools[cls.name] = mk(cls)

        # Geometry construction tools
        for cls in (MidpointTool, AngleBisectorTool, CircumcircleTool,
                    RenamePointTool, MeasureTool,
                    ParallelTool, PerpendicularTool, CompassTool,
                    TangentCircleTool, PointReflectTool, AxisReflectTool, RotateTool,
                    HomothetyTool):
            self._tools[cls.name] = mk(cls)
        self._current_name = "select"
        self._current_tool = self._tools["select"]

        self._shortcuts: dict = dict(_DEFAULT_SHORTCUTS)
        self._load_shortcuts()

    def _load_shortcuts(self):
        cfg = Path(__file__).parent.parent / "config" / "shortcuts.json"
        if cfg.exists():
            try:
                data = json.loads(cfg.read_text(encoding="utf-8"))
                for k, v in data.items():
                    if v in self._tools or v in (
                            "delete_selected", "undo", "redo",
                            "copy_to_clipboard", "save_png", "save_svg",
                            "save_pdf", "zoom_in", "zoom_out", "zoom_fit"):
                        self._shortcuts[k] = v
            except Exception:
                pass

    @property
    def current_tool(self):
        return self._current_tool

    @property
    def current_name(self) -> str:
        return self._current_name

    def activate(self, name: str):
        if name not in self._tools:
            return
        self._current_tool.deactivate()
        self._current_name = name
        self._current_tool = self._tools[name]
        self._current_tool.activate()
        self._scene.set_tool(self._current_tool)
        self.tool_changed.emit(name)

    def set_session(self, scene, history):
        """Chuyển mọi công cụ sang phiên làm việc (tab) khác."""
        self._current_tool.deactivate()
        self._scene, self._history = scene, history
        for tool in self._tools.values():
            tool.scene, tool.history = scene, history
        # Phép quay / vị tự hỏi tham số khi bật → không bật lại khi đổi tab
        name = self._current_name
        if name in ("rotate", "homothety"):
            name = "select"
        self._current_name = name
        self._current_tool = self._tools[name]
        self._current_tool.activate()
        scene.set_tool(self._current_tool)
        self.tool_changed.emit(name)

    def resolve_shortcut(self, key_str: str) -> str:
        return self._shortcuts.get(key_str, "")

    def all_tools(self) -> dict:
        return dict(self._tools)

    def shortcuts(self) -> dict:
        return dict(self._shortcuts)

    def update_shortcut(self, key_str: str, action: str):
        self._shortcuts[key_str] = action
        cfg = Path(__file__).parent.parent / "config" / "shortcuts.json"
        try:
            cfg.write_text(json.dumps(self._shortcuts, indent=2,
                                      ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass
