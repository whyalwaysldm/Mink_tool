"""
Nhập độ dài cạnh (chuột phải → "Số đo cạnh…") cho hình vuông, hình chữ nhật,
hình thoi, hình bình hành, hình thang, hình thang cân. Hình thoi đã nối đường
chéo còn chỉnh được độ dài 2 đường chéo.

Quy ước chung: đỉnh 1 đứng yên, hướng cạnh 1→2 và phía của hình giữ nguyên;
góc của hình giữ nguyên khi chỉ đổi cạnh (hình bình hành, hình thoi).
Đơn vị là đơn vị đo của công cụ Đo đạc.
"""
import math
from PyQt6.QtCore import QPointF
from PyQt6.QtWidgets import (QDialog, QFormLayout, QDoubleSpinBox, QLabel,
                             QDialogButtonBox, QVBoxLayout, QMessageBox)

SIDE_KINDS = ("square", "rectangle", "rhombus", "parallelogram",
              "trapezoid", "isosceles_trapezoid")
_MAX = 100000.0


def shape_for_sides(hits: list):
    """Hình mẫu (cạnh / thân / đỉnh) trong hits có thể nhập độ dài cạnh."""
    from items.shape import shape_of, ShapeItem
    for it in hits:
        shp = shape_of(it)
        if shp is None:
            for d in getattr(it, "_dependents", ()):
                if isinstance(d, ShapeItem) and it in d.points:
                    shp = d
                    break
        if shp is not None and shp.kind in SIDE_KINDS and shp.scene() is not None:
            return shp
    return None


# ── Hình học ─────────────────────────────────────────────────────────────────

def _len(v: QPointF) -> float:
    return math.hypot(v.x(), v.y())


def _unit(v: QPointF) -> QPointF:
    L = _len(v)
    return QPointF(v.x() / L, v.y() / L) if L > 1e-9 else QPointF(1, 0)


def _normal(u: QPointF, toward: QPointF) -> QPointF:
    """Vector đơn vị vuông góc u, cùng phía với toward."""
    n = QPointF(-u.y(), u.x())
    return n if n.x() * toward.x() + n.y() * toward.y() >= 0 else -n


def diagonal_segments(scene, pts_items: list) -> tuple:
    """(có đường chéo 1–3, có đường chéo 2–4) — đoạn nối 2 đỉnh đối nhau."""
    from items.segment import SegmentItem
    pairs = [{pts_items[0], pts_items[2]}, {pts_items[1], pts_items[3]}]
    found = [False, False]
    for it in scene.items():
        if isinstance(it, SegmentItem):
            for k, pr in enumerate(pairs):
                if {it.p1, it.p2} == pr:
                    found[k] = True
    return tuple(found)


def current_values(kind: str, P: list) -> dict:
    side = lambda i, j: _len(P[j] - P[i])
    if kind == "square":
        return {"a": side(0, 1)}
    if kind in ("rectangle", "parallelogram"):
        return {"a": side(0, 1), "b": side(0, 3)}
    if kind == "rhombus":
        return {"a": side(0, 1), "p": side(0, 2), "q": side(1, 3)}
    if kind == "isosceles_trapezoid":
        return {"a": side(0, 1), "b": side(2, 3), "c": side(0, 3)}
    if kind == "trapezoid":
        return {"a": side(0, 1), "b": side(2, 3), "c": side(0, 3), "d": side(1, 2)}
    return {}


def side_targets(kind: str, P: list, v: dict):
    """Vị trí mới 4 đỉnh từ các số đo v; None nếu không dựng được."""
    A = P[0]
    u = _unit(P[1] - P[0])
    if kind == "square":
        n = _normal(u, P[3] - P[0])
        a = v["a"]
        return [A, A + u * a, A + u * a + n * a, A + n * a]
    if kind == "rectangle":
        n = _normal(u, P[3] - P[0])
        return [A, A + u * v["a"], A + u * v["a"] + n * v["b"], A + n * v["b"]]
    if kind == "parallelogram":
        w = _unit(P[3] - P[0])        # giữ góc tại đỉnh 1
        return [A, A + u * v["a"], A + u * v["a"] + w * v["b"], A + w * v["b"]]
    if kind == "rhombus":
        if "p" in v:                  # theo 2 đường chéo, giữ hướng chéo 1–3
            e = _unit(P[2] - P[0])
            f = _normal(e, P[1] - P[0])
            c = A + e * (v["p"] / 2)
            return [A, c + f * (v["q"] / 2), A + e * v["p"], c - f * (v["q"] / 2)]
        w = _unit(P[3] - P[0])        # chỉ đổi cạnh: giữ góc
        return [A, A + u * v["a"], A + u * v["a"] + w * v["a"], A + w * v["a"]]
    n = _normal(u, P[3] - P[0])
    a, b = v["a"], v["b"]
    if kind == "isosceles_trapezoid":
        x = (a - b) / 2
        c = v["c"]
        if c <= abs(x) + 1e-9:
            return None
        h = math.sqrt(c * c - x * x)
        D = A + u * x + n * h
        return [A, A + u * a, D + u * b, D]
    if kind == "trapezoid":
        c, d = v["c"], v["d"]         # AD, BC
        k = a - b
        if abs(k) < 1e-9:
            if abs(c - d) > 1e-6:
                return None
            x = (P[3] - P[0]).x() * u.x() + (P[3] - P[0]).y() * u.y()
        else:
            x = (c * c - d * d + k * k) / (2 * k)
        if c <= abs(x) + 1e-9:
            return None
        h = math.sqrt(c * c - x * x)
        D = A + u * x + n * h
        return [A, A + u * a, D + u * b, D]
    return None


# ── Hộp thoại ────────────────────────────────────────────────────────────────

class _SidesDialog(QDialog):
    def __init__(self, parent, kind: str, label: str, names: list, vals: dict,
                 diag: tuple):
        super().__init__(parent)
        self.setWindowTitle(f"Số đo cạnh — {label}")
        self._kind = kind
        A, B, C, D = names
        rows = {
            "square": [("a", f"Cạnh {A}{B}:")],
            "rectangle": [("a", f"Cạnh {A}{B}:"), ("b", f"Cạnh {A}{D}:")],
            "parallelogram": [("a", f"Cạnh {A}{B}:"), ("b", f"Cạnh {A}{D}:")],
            "rhombus": [("a", f"Cạnh {A}{B}:")],
            "isosceles_trapezoid": [("a", f"Đáy {A}{B}:"), ("b", f"Đáy {D}{C}:"),
                                    ("c", f"Cạnh bên {A}{D} = {B}{C}:")],
            "trapezoid": [("a", f"Đáy {A}{B}:"), ("b", f"Đáy {D}{C}:"),
                          ("c", f"Cạnh bên {A}{D}:"), ("d", f"Cạnh bên {B}{C}:")],
        }[kind]
        self._diag = kind == "rhombus" and any(diag)
        if self._diag:
            rows += [("p", f"Đường chéo {A}{C}:"), ("q", f"Đường chéo {B}{D}:")]
        form = QFormLayout()
        self._spins = {}
        for key, text in rows:
            s = QDoubleSpinBox()
            s.setDecimals(1)
            s.setRange(1.0, _MAX)
            s.setValue(round(vals[key], 1))
            form.addRow(text, s)
            self._spins[key] = s
        self._info = QLabel()
        form.addRow("", self._info)
        self._sync = False
        if self._diag:
            # Đổi cạnh → 2 đường chéo co giãn theo (giữ góc); đổi đường chéo
            # → cạnh tính lại
            self._spins["a"].valueChanged.connect(self._side_changed)
            self._spins["p"].valueChanged.connect(self._diag_changed)
            self._spins["q"].valueChanged.connect(self._diag_changed)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addLayout(form)
        lay.addWidget(buttons)

    def _side_changed(self, a):
        if self._sync:
            return
        p, q = self._spins["p"].value(), self._spins["q"].value()
        cur = math.hypot(p, q) / 2 or 1.0
        self._sync = True
        self._spins["p"].setValue(p * a / cur)
        self._spins["q"].setValue(q * a / cur)
        self._sync = False

    def _diag_changed(self, *_):
        if self._sync:
            return
        self._sync = True
        self._spins["a"].setValue(math.hypot(self._spins["p"].value(),
                                             self._spins["q"].value()) / 2)
        self._sync = False

    def values(self) -> dict:
        v = {k: s.value() for k, s in self._spins.items()}
        if not self._diag:
            v.pop("p", None)
            v.pop("q", None)
        return v


def edit_shape_sides(shape, scene, history) -> bool:
    items = shape.points
    if len(items) != 4:
        return False
    P = [p.scenePos() for p in items]
    names = [getattr(p, "label", "") or "ABCD"[i] for i, p in enumerate(items)]
    views = scene.views()
    parent = views[0] if views else None
    diag = diagonal_segments(scene, items) if shape.kind == "rhombus" else (False, False)
    dlg = _SidesDialog(parent, shape.kind, shape.shape_label, names,
                       current_values(shape.kind, P), diag)
    if dlg.exec() != QDialog.DialogCode.Accepted:
        return False
    out = side_targets(shape.kind, P, dlg.values())
    if out is None:
        QMessageBox.information(parent, "Số đo cạnh",
                                f"Không dựng được {shape.shape_label.lower()} "
                                "với các số đo này.")
        return False
    moves = [(it, QPointF(it.pos()), it.pos() + (out[i] - P[i]))
             for i, it in enumerate(items)
             if (out[i] - P[i]).manhattanLength() > 1e-9]
    stuck = [names[items.index(m[0])] for m in moves
             if getattr(m[0], "is_constrained", False)]
    if stuck:
        QMessageBox.information(parent, "Số đo cạnh",
                                f"Không đổi được: {', '.join(stuck)} là điểm "
                                "dựng hình, không di chuyển tự do được.")
        return False
    if moves:
        history.push_move_group(moves)
    return True
